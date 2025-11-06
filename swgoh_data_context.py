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

        # Track seen attacks to avoid counting duplicates
        # Key: (attacker_id, defender_id, defending_leader, successful_defends)
        seen_attacks = set()

        # Handle both data structures: 'events' (old) and 'data' (new)
        events = self.tw_data.get('data', self.tw_data.get('events', []))

        for event in events:
            # Get the activity log message key from the nested structure
            payload = event.get('payload', {})
            zone_data = payload.get('zoneData', {})
            activity_log = zone_data.get('activityLogMessage', {})
            event_type = activity_log.get('key', '')

            # Process attack events:
            # - SQUAD_WIN events (squadStatus: 3) = wins
            # - EMPTY events with warSquad = holds (both squadStatus: 1 and 2)
            is_win = event_type == 'TERRITORY_CHANNEL_ACTIVITY_CONFLICT_SQUAD_WIN'
            is_hold = event_type == 'EMPTY'

            war_squad = payload.get('warSquad', {})

            # Skip EMPTY events without warSquad (these are zone clearing events, not attacks)
            if is_hold and not war_squad:
                continue

            # Skip if not an attack event
            if not is_win and not is_hold:
                continue

            info = event.get('info', {})

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

            # Extract defending squad leader (first unit in cell array, cellIndex 0)
            defending_leader = None
            squad = war_squad.get('squad') if war_squad else None
            cells = squad.get('cell', []) if squad else []
            if cells:
                # Find the cell with cellIndex 0 (leader position)
                for cell in cells:
                    if cell.get('cellIndex') == 0:
                        # Extract unit definition ID (e.g., "CHIEFCHIRPA:SEVEN_STAR")
                        unit_def_id = cell.get('unitDefId', '')
                        # Remove the :SEVEN_STAR suffix to get character ID
                        if ':' in unit_def_id:
                            defending_leader = unit_def_id.split(':')[0]
                        else:
                            defending_leader = unit_def_id
                        break

            # Determine result type
            # squadStatus: 3 = win (SQUAD_WIN event - attacker defeated defense)
            # squadStatus: 1 = hold (EMPTY event - defense held, attacker failed/forfeited)
            # Note: squadStatus: 2 events are skipped (lock state indicators, not actual attacks)
            # We cannot distinguish between "forfeit" and "loss" from the data - both are holds
            squad_status = war_squad.get('squadStatus')

            if is_win or squad_status == 3:
                result_type = 'win'
            else:  # squadStatus 1 = hold (defense held)
                result_type = 'hold'

            # Create unique key to detect duplicate events
            # When an attack wins, both a SQUAD_WIN and an EMPTY/squadStatus:2 event are logged
            # We deduplicate using (attacker, defender, leader, successfulDefends)
            successful_defends = war_squad.get('successfulDefends', 0)
            attack_key = (
                info.get('authorId', ''),
                war_squad.get('playerId', ''),
                defending_leader,
                successful_defends
            )

            # Skip if we've already processed this attack
            if attack_key in seen_attacks:
                continue

            seen_attacks.add(attack_key)

            # Extract attack data
            # CRITICAL: authorId/authorName is the ATTACKER
            # warSquad.playerId/playerName is the DEFENDER
            attack_data = {
                'attacker_id': info.get('authorId', ''),
                'attacker_name': info.get('authorName', ''),
                'defender_id': war_squad.get('playerId', ''),
                'defender_name': war_squad.get('playerName', ''),
                'defending_leader': defending_leader,
                'zone_id': zone_data.get('zoneId', ''),
                'attacking_guild_id': zone_data.get('guildId', ''),
                'banners': banners,
                'squad_power': war_squad.get('power', 0),
                'is_win': is_win,  # True = attacker won, False = defense held
                'result_type': result_type,  # 'win' or 'hold'
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

        # Get defending leader statistics (leaders we faced when attacking)
        our_stats['defending_leaders_we_faced'] = self._get_defending_leader_stats(our_df, limit=10)

        # Get defending leader statistics (our leaders that opponent faced when they attacked us)
        our_stats['our_defending_leaders'] = self._get_defending_leader_stats(opponent_df, limit=10)

        # Get detailed per-squad statistics (enemy squads we attacked)
        our_stats['detailed_enemy_squads'] = self._get_detailed_defending_squads(our_df)

        # Get detailed per-squad statistics (our squads that opponent attacked)
        our_stats['detailed_our_squads'] = self._get_detailed_defending_squads(opponent_df)

        # Get defense contributor statistics (who deployed and how they performed)
        our_stats['defense_contributors'] = self._get_defense_contributors()

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

    def _get_detailed_defending_squads(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Get detailed statistics for each unique defending squad (by player + leader).

        Args:
            df: DataFrame containing attack data

        Returns:
            List of detailed squad statistics sorted by hold rate
        """
        if df.empty:
            return []

        # Filter out rows where defending_leader is None or defender info is missing
        df_valid = df[(df['defending_leader'].notna()) & (df['defender_name'].notna())]

        if df_valid.empty:
            return []

        # Group by defender_name AND defending_leader (unique squad instances)
        squad_groups = df_valid.groupby(['defender_name', 'defending_leader'])

        squad_stats_list = []
        for (defender_name, leader), group in squad_groups:
            total_attempts = len(group)
            wins = (group['result_type'] == 'win').sum()
            holds = (group['result_type'] == 'hold').sum()

            win_rate = (wins / total_attempts * 100) if total_attempts > 0 else 0
            hold_rate = (holds / total_attempts * 100) if total_attempts > 0 else 0

            # Average banners when opponent won
            wins_only = group[group['result_type'] == 'win']
            avg_banners_on_wins = wins_only['banners'].mean() if len(wins_only) > 0 else 0

            squad_stats_list.append({
                'defender_name': defender_name,
                'leader': leader,
                'total_attempts': total_attempts,
                'wins': wins,
                'holds': holds,
                'win_rate': win_rate,
                'hold_rate': hold_rate,
                'avg_banners_on_wins': avg_banners_on_wins
            })

        # Convert to DataFrame for sorting
        squad_stats_df = pd.DataFrame(squad_stats_list)

        # Sort by hold_rate descending, then by total_attempts descending
        squad_stats_df = squad_stats_df.sort_values(['hold_rate', 'total_attempts'], ascending=[False, False])

        return squad_stats_df.to_dict('records')

    def _get_defending_leader_stats(self, df: pd.DataFrame, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get statistics on defending leaders (leaders we faced in attacks).

        Args:
            df: DataFrame containing attack data
            limit: Maximum number of leaders to return

        Returns:
            List of leader statistics dictionaries with win rate and hold rate
        """
        if df.empty:
            return []

        # Filter out rows where defending_leader is None
        df_with_leaders = df[df['defending_leader'].notna()]

        if df_with_leaders.empty:
            return []

        # Group by defending leader and calculate stats
        leader_groups = df_with_leaders.groupby('defending_leader')

        leader_stats_list = []
        for leader, group in leader_groups:
            total_attempts = len(group)
            wins = (group['result_type'] == 'win').sum()
            holds = (group['result_type'] == 'hold').sum()

            # Calculate rates
            win_rate = (wins / total_attempts * 100) if total_attempts > 0 else 0
            hold_rate = (holds / total_attempts * 100) if total_attempts > 0 else 0

            # Average banners when we DID win
            wins_only = group[group['result_type'] == 'win']
            avg_banners_on_wins = wins_only['banners'].mean() if len(wins_only) > 0 else 0

            leader_stats_list.append({
                'leader': leader,
                'total_attempts': total_attempts,
                'wins': wins,
                'holds': holds,
                'win_rate': win_rate,
                'hold_rate': hold_rate,
                'avg_banners_on_wins': avg_banners_on_wins
            })

        # Convert to DataFrame for sorting
        leader_stats_df = pd.DataFrame(leader_stats_list)

        # Sort by hold_rate descending (leaders we struggled against most)
        leader_stats_df = leader_stats_df.sort_values('hold_rate', ascending=False)

        # Convert to list of dicts
        return leader_stats_df.head(limit).to_dict('records')

    def _get_defense_contributors(self) -> List[Dict[str, Any]]:
        """
        Get statistics on who deployed defenses and how those defenses performed.

        IMPORTANT: Deployment events are a snapshot of UNTOUCHED defenses.
        When a squad is attacked, its deployment event is removed from the logs.
        Therefore, we must combine:
        1. Attack logs (opponent attacks on us) = squads that WERE attacked
        2. Deployment events = squads that were NEVER attacked (untouched)

        This gives us the complete picture of all defenses set.

        Returns:
            List of player defense statistics sorted by total holds
        """
        if not self.tw_data:
            return []

        # Parse defense deployments for our guild (untouched defenses only)
        deployments = []
        events = self.tw_data.get('data', self.tw_data.get('events', []))

        for event in events:
            payload = event.get('payload', {})
            zone_data = payload.get('zoneData', {})
            activity_log = zone_data.get('activityLogMessage', {})
            event_type = activity_log.get('key', '')

            # Process both squad and fleet deployments
            is_squad_deploy = event_type == 'TERRITORY_CHANNEL_ACTIVITY_CONFLICT_DEFENSE_DEPLOY'
            is_fleet_deploy = event_type == 'TERRITORY_CHANNEL_ACTIVITY_CONFLICT_DEFENSE_FLEET_DEPLOY'

            if is_squad_deploy or is_fleet_deploy:
                guild_id = zone_data.get('guildId', '')

                # Only process our guild's deployments
                if guild_id == self.guild_id:
                    info = event.get('info', {})
                    war_squad = payload.get('warSquad', {})

                    # Get leader
                    defending_leader = None
                    squad = war_squad.get('squad') if war_squad else None
                    if squad:
                        cells = squad.get('cell', [])
                        for cell in cells:
                            if cell.get('cellIndex') == 0:
                                unit_def_id = cell.get('unitDefId', '')
                                if ':' in unit_def_id:
                                    defending_leader = unit_def_id.split(':')[0]
                                break

                    deployments.append({
                        'player_id': info.get('authorId', ''),
                        'player_name': info.get('authorName', ''),
                        'leader': defending_leader,
                        'power': war_squad.get('power', 0) if war_squad else 0,
                    })

        # Get attack results (opponent attacks on us)
        _, opponent_df = self._parse_tw_attacks()

        # Combine deployment data with attack data to get complete picture
        # Deployment events only show UNTOUCHED squads (never attacked)
        # Attack logs show squads that WERE attacked
        # Together they give us ALL squads that were deployed

        if deployments:
            deployments_df = pd.DataFrame(deployments)

            # Add squads from attack logs that weren't in deployment events
            if not opponent_df.empty:
                # Get unique defender squads from attacks
                attacked_squads = opponent_df[['defender_name', 'defending_leader']].drop_duplicates()

                # Find squads in attack logs but not in deployments
                for _, row in attacked_squads.iterrows():
                    defender = row['defender_name']
                    leader = row['defending_leader']

                    # Check if this squad is already in deployments
                    existing = deployments_df[
                        (deployments_df['player_name'] == defender) &
                        (deployments_df['leader'] == leader)
                    ]

                    if existing.empty and pd.notna(leader):
                        # Add inferred deployment
                        # Get power from first attack on this squad
                        squad_attacks = opponent_df[
                            (opponent_df['defender_name'] == defender) &
                            (opponent_df['defending_leader'] == leader)
                        ]
                        avg_power = squad_attacks['squad_power'].mean() if len(squad_attacks) > 0 else 0

                        deployments_df = pd.concat([deployments_df, pd.DataFrame([{
                            'player_id': '',
                            'player_name': defender,
                            'leader': leader,
                            'power': avg_power,
                        }])], ignore_index=True)
        elif not opponent_df.empty:
            # No deployment events at all, infer everything from attacks
            attacked_squads = opponent_df[['defender_name', 'defending_leader', 'squad_power']].copy()
            attacked_squads = attacked_squads.rename(columns={
                'defender_name': 'player_name',
                'defending_leader': 'leader',
                'squad_power': 'power'
            })
            # Get average power per unique squad
            deployments_df = attacked_squads.groupby(['player_name', 'leader'], as_index=False)['power'].mean()
            deployments_df['player_id'] = ''
        else:
            return []

        # Match deployments to attack results by defender_name and defending_leader
        # Count squads deployed per player
        player_stats_list = []

        for player_name, player_group in deployments_df.groupby('player_name'):
            squads_deployed = len(player_group)
            avg_squad_power = player_group['power'].mean()

            # Find attacks on this player's squads
            player_attacks = opponent_df[opponent_df['defender_name'] == player_name]

            if len(player_attacks) > 0:
                total_attempts = len(player_attacks)
                wins = (player_attacks['result_type'] == 'win').sum()
                holds = (player_attacks['result_type'] == 'hold').sum()
                win_rate = (wins / total_attempts * 100) if total_attempts > 0 else 0
                hold_rate = (holds / total_attempts * 100) if total_attempts > 0 else 0

                # Banners given up (when opponent won)
                wins_only = player_attacks[player_attacks['result_type'] == 'win']
                banners_given_up = wins_only['banners'].sum()
                avg_banners_given_up = wins_only['banners'].mean() if len(wins_only) > 0 else 0
            else:
                # No attacks on this player's squads (untouched defenses)
                total_attempts = 0
                wins = 0
                holds = 0
                win_rate = 0
                hold_rate = 0
                banners_given_up = 0
                avg_banners_given_up = 0

            player_stats_list.append({
                'player_name': player_name,
                'squads_deployed': squads_deployed,
                'avg_squad_power': avg_squad_power,
                'total_attempts': total_attempts,
                'wins': wins,
                'holds': holds,
                'win_rate': win_rate,
                'hold_rate': hold_rate,
                'banners_given_up': banners_given_up,
                'avg_banners_given_up': avg_banners_given_up,
            })

        # Convert to DataFrame and sort by total holds (most valuable defenders)
        stats_df = pd.DataFrame(player_stats_list)
        stats_df = stats_df.sort_values(['holds', 'squads_deployed'], ascending=[False, False])

        return stats_df.to_dict('records')

    def get_participation_report(self, min_banners: int = 50, min_attacks: int = 1, expected_roster: list = None, use_guild_roster: bool = True) -> Dict[str, Any]:
        """
        Get participation report showing who participated and who underperformed.

        Args:
            min_banners: Minimum banners threshold for adequate participation
            min_attacks: Minimum attacks threshold
            expected_roster: Optional list of player names expected to participate
            use_guild_roster: If True and guild data is loaded, automatically use guild roster

        Returns:
            Dictionary with participation statistics and underperformer lists
        """
        if not self.tw_data:
            return {}

        our_df, _ = self._parse_tw_attacks()

        if our_df.empty:
            return {
                'total_players': 0,
                'players_who_attacked': 0,
                'players_who_defended': 0,
                'underperformers': [],
                'non_participants': [],
            }

        # Get offensive stats (attacks)
        offensive_stats = our_df.groupby(['attacker_id', 'attacker_name']).agg({
            'banners': 'sum',
            'is_win': 'sum',  # Total wins
            'result_type': 'count'  # Total attacks
        }).reset_index()
        offensive_stats.columns = ['player_id', 'player_name', 'total_banners', 'wins', 'attacks']

        # Get defensive stats
        defense_contributors = self._get_defense_contributors()
        defense_df = pd.DataFrame(defense_contributors) if defense_contributors else pd.DataFrame()

        # Count squads vs fleets for each player (to calculate deployment banners)
        # We need to parse deployments again to distinguish squads from fleets
        events = self.tw_data.get('data', self.tw_data.get('events', []))
        deployment_banners = {}

        for event in events:
            payload = event.get('payload', {})
            zone_data = payload.get('zoneData', {})
            activity_log = zone_data.get('activityLogMessage', {})
            event_type = activity_log.get('key', '')

            if zone_data.get('guildId', '') == self.guild_id:
                info = event.get('info', {})
                player_name = info.get('authorName', '')

                if event_type == 'TERRITORY_CHANNEL_ACTIVITY_CONFLICT_DEFENSE_DEPLOY':
                    # Squad deployment: +30 banners
                    if player_name not in deployment_banners:
                        deployment_banners[player_name] = {'squads': 0, 'fleets': 0}
                    deployment_banners[player_name]['squads'] += 1
                elif event_type == 'TERRITORY_CHANNEL_ACTIVITY_CONFLICT_DEFENSE_FLEET_DEPLOY':
                    # Fleet deployment: +34 banners
                    if player_name not in deployment_banners:
                        deployment_banners[player_name] = {'squads': 0, 'fleets': 0}
                    deployment_banners[player_name]['fleets'] += 1

        # Create comprehensive participation list
        all_players = set()

        # Add offensive players
        for _, row in offensive_stats.iterrows():
            all_players.add(row['player_name'])

        # Add defensive players
        if not defense_df.empty:
            for _, row in defense_df.iterrows():
                all_players.add(row['player_name'])

        # Add players from deployment banners
        for player_name in deployment_banners.keys():
            all_players.add(player_name)

        # If guild data loaded and use_guild_roster is True, use it automatically
        if use_guild_roster and self.guild_data:
            roster = self.get_guild_roster()
            if roster:
                logger.info(f"Adding {len(roster)} players from guild roster")
                for player_name in roster:
                    all_players.add(player_name)
        # Otherwise, if roster provided manually, add any missing players
        elif expected_roster:
            for player_name in expected_roster:
                all_players.add(player_name)

        # Build participation report
        participation_list = []

        for player_name in all_players:
            # Get offensive stats
            player_offense = offensive_stats[offensive_stats['player_name'] == player_name]
            if not player_offense.empty:
                attacks = int(player_offense['attacks'].iloc[0])
                offensive_banners = int(player_offense['total_banners'].iloc[0])
                wins = int(player_offense['wins'].iloc[0])
            else:
                attacks = 0
                offensive_banners = 0
                wins = 0

            # Get defensive stats
            if not defense_df.empty:
                player_defense = defense_df[defense_df['player_name'] == player_name]
                if not player_defense.empty:
                    squads_deployed = int(player_defense['squads_deployed'].iloc[0])
                    defensive_holds = int(player_defense['holds'].iloc[0])
                else:
                    squads_deployed = 0
                    defensive_holds = 0
            else:
                squads_deployed = 0
                defensive_holds = 0

            # Calculate deployment banners
            defensive_banners = 0
            if player_name in deployment_banners:
                squads = deployment_banners[player_name]['squads']
                fleets = deployment_banners[player_name]['fleets']
                defensive_banners = (squads * 30) + (fleets * 34)

            # Total banners = offensive + defensive deployment bonuses
            total_banners = offensive_banners + defensive_banners

            # Determine participation status
            participated_offense = attacks >= min_attacks
            participated_defense = squads_deployed > 0
            underperforming = participated_offense and total_banners < min_banners

            participation_list.append({
                'player_name': player_name,
                'attacks': attacks,
                'offensive_banners': offensive_banners,
                'defensive_banners': defensive_banners,
                'total_banners': total_banners,
                'wins': wins,
                'squads_deployed': squads_deployed,
                'defensive_holds': defensive_holds,
                'participated_offense': participated_offense,
                'participated_defense': participated_defense,
                'underperforming': underperforming,
            })

        # Sort by total banners descending
        participation_df = pd.DataFrame(participation_list)
        participation_df = participation_df.sort_values('total_banners', ascending=False)

        # Identify underperformers and non-participants
        underperformers = participation_df[participation_df['underperforming'] == True].to_dict('records')
        non_participants = participation_df[
            (participation_df['participated_offense'] == False) &
            (participation_df['participated_defense'] == False)
        ].to_dict('records')

        return {
            'total_players': len(all_players),
            'players_who_attacked': int((participation_df['attacks'] > 0).sum()),
            'players_who_defended': int((participation_df['squads_deployed'] > 0).sum()),
            'min_banners_threshold': min_banners,
            'underperformers': underperformers,
            'non_participants': non_participants,
            'all_participants': participation_df.to_dict('records'),
        }

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
                content = f.read()

            # Handle files that have header text before JSON
            json_start = content.find('{')
            if json_start > 0:
                content = content[json_start:]

            self.guild_data = json.loads(content)
            logger.info(f"Loaded guild data from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load guild data: {e}")
            return False

    def get_guild_roster(self) -> List[str]:
        """
        Extract the list of player names from loaded guild data.

        Returns:
            List of player names in the guild, or empty list if no guild data loaded
        """
        if not self.guild_data:
            logger.warning("No guild data loaded")
            return []

        try:
            # Navigate to the member list
            # Structure: events -> guild -> member -> [{ playerName: "..." }]
            events = self.guild_data.get('events', {})
            guild = events.get('guild', {})
            members = guild.get('member', [])

            roster = [member.get('playerName', '') for member in members if member.get('playerName')]
            logger.info(f"Extracted {len(roster)} player names from guild data")
            return roster

        except Exception as e:
            logger.error(f"Failed to extract guild roster: {e}")
            return []

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
