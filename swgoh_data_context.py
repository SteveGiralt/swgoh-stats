#!/usr/bin/env python3
"""
SWGOH Data Context Builder

This module handles loading, processing, and summarizing SWGOH data
(particularly TW logs) for use in AI-powered analysis. It provides
token-aware summarization to fit within LLM context windows.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class SWGOHDataContext:
    """
    Builds and manages data context for AI analysis of SWGOH data.

    Handles loading TW logs, guild data, and player data, then creates
    smart summaries that fit within token budgets while maintaining
    critical information for analysis.
    """

    def __init__(self, guild_id: str = "BQ4f8IJyRma4IWSSCurp4Q", guild_name: str = "DarthJedii56"):
        """
        Initialize the data context builder.

        Args:
            guild_id: The guild ID to use for filtering our guild's data
            guild_name: The guild name for display purposes
        """
        self.guild_id = guild_id
        self.guild_name = guild_name
        self.tw_data = None
        self.guild_data = None
        self.player_data = {}

    def load_tw_logs(self, file_path: str) -> bool:
        """
        Load Territory Wars logs from a JSON file.

        Args:
            file_path: Path to the TW logs JSON file

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Handle files that have header text before JSON
            # (from --output flag in swgoh_api_client.py)
            json_start = content.find('{')
            if json_start > 0:
                content = content[json_start:]

            self.tw_data = json.loads(content)
            logger.info(f"Loaded TW logs from {file_path}")
            return True

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error loading TW logs: {e}")
            return False

    def _parse_tw_attacks(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Parse TW logs into DataFrames for our guild and opponent guild.

        Returns:
            Tuple of (our_attacks_df, opponent_attacks_df)
        """
        if not self.tw_data:
            return pd.DataFrame(), pd.DataFrame()

        our_attacks = []
        opponent_attacks = []

        # Handle both data structures: 'events' (old) and 'data' (new)
        events = self.tw_data.get('data', self.tw_data.get('events', []))

        for event in events:
            # Get the activity log message key from the nested structure
            payload = event.get('payload', {})
            zone_data = payload.get('zoneData', {})
            activity_log = zone_data.get('activityLogMessage', {})
            event_type = activity_log.get('key', '')

            # Only process successful attacks (SQUAD_WIN events)
            if event_type != 'TERRITORY_CHANNEL_ACTIVITY_CONFLICT_SQUAD_WIN':
                continue

            info = event.get('info', {})
            war_squad = payload.get('warSquad', {})

            # Extract banner count from params
            params = activity_log.get('param', [])
            banners = 0
            if params and len(params) > 0:
                param_values = params[0].get('paramValue', [])
                if param_values:
                    try:
                        banners = int(param_values[0])
                    except (ValueError, IndexError):
                        banners = 0

            # Extract attack data
            # CRITICAL: authorId/authorName is the ATTACKER (who won)
            # warSquad.playerId/playerName is the DEFENDER (who lost)
            attack_data = {
                'attacker_id': info.get('authorId', ''),
                'attacker_name': info.get('authorName', ''),
                'defender_id': war_squad.get('playerId', ''),
                'defender_name': war_squad.get('playerName', ''),
                'zone_id': zone_data.get('zoneId', ''),
                'attacking_guild_id': zone_data.get('guildId', ''),
                'banners': banners,
                'squad_power': war_squad.get('power', 0),
            }

            # Separate by attacking guild
            if attack_data['attacking_guild_id'] == self.guild_id:
                our_attacks.append(attack_data)
            else:
                opponent_attacks.append(attack_data)

        our_df = pd.DataFrame(our_attacks)
        opponent_df = pd.DataFrame(opponent_attacks)

        return our_df, opponent_df

    def get_tw_summary(self, max_tokens: int = 2000) -> Dict[str, Any]:
        """
        Generate a summary of TW logs suitable for LLM context.

        Creates a token-aware summary with key statistics, top performers,
        and guild comparisons. Aims to stay within the specified token budget.

        Args:
            max_tokens: Target maximum tokens for the summary (approximate)

        Returns:
            Dictionary containing summary statistics
        """
        if not self.tw_data:
            logger.warning("No TW data loaded")
            return {}

        our_df, opponent_df = self._parse_tw_attacks()

        if our_df.empty:
            logger.warning("No attacks found for our guild")
            return {
                'guild_name': self.guild_name,
                'total_attacks': 0,
                'total_banners': 0,
                'unique_players': 0,
                'avg_banners': 0.0,
                'avg_power': 0.0,
            }

        # Calculate our guild statistics
        our_stats = self._calculate_guild_stats(our_df)
        our_stats['guild_name'] = self.guild_name

        # Calculate opponent statistics
        opponent_stats = self._calculate_guild_stats(opponent_df)
        our_stats['opponent_stats'] = opponent_stats

        # Get top performers (for detailed summary)
        our_stats['top_performers'] = self._get_top_performers(our_df, limit=10)

        # Store full dataframes for potential detailed queries
        our_stats['_our_df'] = our_df
        our_stats['_opponent_df'] = opponent_df

        return our_stats

    def _calculate_guild_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate statistics for a guild's attacks.

        Args:
            df: DataFrame containing attack data

        Returns:
            Dictionary with guild statistics
        """
        if df.empty:
            return {
                'total_attacks': 0,
                'total_banners': 0,
                'unique_players': 0,
                'avg_banners': 0.0,
                'avg_power': 0.0,
            }

        return {
            'total_attacks': len(df),
            'total_banners': df['banners'].sum(),
            'unique_players': df['attacker_id'].nunique(),
            'avg_banners': df['banners'].mean(),
            'avg_power': df['squad_power'].mean(),
        }

    def _get_top_performers(self, df: pd.DataFrame, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top performing players sorted by total banners.

        Args:
            df: DataFrame containing attack data
            limit: Maximum number of players to return

        Returns:
            List of player statistics dictionaries
        """
        if df.empty:
            return []

        # Group by player
        player_stats = df.groupby(['attacker_id', 'attacker_name']).agg({
            'banners': ['sum', 'mean', 'count'],
            'squad_power': 'mean'
        }).reset_index()

        # Flatten column names
        player_stats.columns = ['player_id', 'name', 'total_banners', 'avg_banners', 'attacks', 'avg_power']

        # Sort by total banners descending
        player_stats = player_stats.sort_values('total_banners', ascending=False)

        # Convert to list of dicts
        return player_stats.head(limit).to_dict('records')

    def get_player_details(self, player_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed statistics for a specific player.

        Args:
            player_name: Name of the player to look up

        Returns:
            Dictionary with player statistics, or None if not found
        """
        if not self.tw_data:
            return None

        our_df, _ = self._parse_tw_attacks()

        if our_df.empty:
            return None

        # Filter for the specific player (case-insensitive partial match)
        player_df = our_df[our_df['attacker_name'].str.contains(player_name, case=False, na=False)]

        if player_df.empty:
            return None

        # Calculate detailed stats
        stats = {
            'name': player_df['attacker_name'].iloc[0],
            'player_id': player_df['attacker_id'].iloc[0],
            'total_attacks': len(player_df),
            'total_banners': player_df['banners'].sum(),
            'avg_banners': player_df['banners'].mean(),
            'min_banners': player_df['banners'].min(),
            'max_banners': player_df['banners'].max(),
            'avg_power': player_df['squad_power'].mean(),
            'total_power': player_df['squad_power'].sum(),
        }

        # Add banner efficiency tier
        avg_banners = stats['avg_banners']
        if avg_banners >= 60:
            stats['efficiency_tier'] = 'High'
        elif avg_banners >= 40:
            stats['efficiency_tier'] = 'Medium'
        else:
            stats['efficiency_tier'] = 'Low'

        # Add zone breakdown
        zone_counts = player_df['zone_id'].value_counts().to_dict()
        stats['zones_attacked'] = zone_counts

        return stats

    def get_full_player_list(self) -> List[Dict[str, Any]]:
        """
        Get complete list of all players who attacked.

        Returns:
            List of all player statistics
        """
        if not self.tw_data:
            return []

        our_df, _ = self._parse_tw_attacks()

        if our_df.empty:
            return []

        # Group by player
        player_stats = our_df.groupby(['attacker_id', 'attacker_name']).agg({
            'banners': ['sum', 'mean', 'count'],
            'squad_power': 'mean'
        }).reset_index()

        # Flatten column names
        player_stats.columns = ['player_id', 'name', 'total_banners', 'avg_banners', 'attacks', 'avg_power']

        # Sort by total banners descending
        player_stats = player_stats.sort_values('total_banners', ascending=False)

        return player_stats.to_dict('records')

    def compare_players(self, player_names: List[str]) -> Dict[str, Any]:
        """
        Compare statistics for multiple players.

        Args:
            player_names: List of player names to compare

        Returns:
            Dictionary with comparison data
        """
        comparison = {
            'players': [],
            'comparison_found': False
        }

        for name in player_names:
            player_stats = self.get_player_details(name)
            if player_stats:
                comparison['players'].append(player_stats)
                comparison['comparison_found'] = True

        return comparison

    def load_guild_data(self, file_path: str) -> bool:
        """
        Load guild data from a JSON file.

        Args:
            file_path: Path to the guild data JSON file

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(file_path, 'r') as f:
                self.guild_data = json.load(f)
            logger.info(f"Loaded guild data from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load guild data: {e}")
            return False

    def load_player_data(self, file_path: str, ally_code: str) -> bool:
        """
        Load player data from a JSON file.

        Args:
            file_path: Path to the player data JSON file
            ally_code: Ally code for this player (used as key)

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(file_path, 'r') as f:
                self.player_data[ally_code] = json.load(f)
            logger.info(f"Loaded player data for {ally_code} from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load player data: {e}")
            return False

    def get_context_summary(self) -> str:
        """
        Get a formatted summary of all loaded data for LLM context.

        Returns:
            Formatted string suitable for LLM context
        """
        from swgoh_prompts import format_tw_summary

        summary_stats = self.get_tw_summary()
        return format_tw_summary(summary_stats)
