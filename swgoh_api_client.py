#!/usr/bin/env python3
"""
SWGOH API Client for Mhanndalorian Bot
A client for interacting with the Mhanndalorian Bot API to retrieve SWGOH data.
"""

import os
import sys
import time
import hashlib
import hmac
import json
import argparse
import logging
from typing import Dict, List, Optional, Any
from pprint import pprint
from pathlib import Path

import requests
import pandas as pd
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SWGOHAPIClient:
    """Client for interacting with the Mhanndalorian Bot API."""

    BASE_URL = "https://mhanndalorianbot.work"
    API_ENDPOINT = "/api"

    def __init__(self, api_key: str, discord_id: str, use_hmac: bool = False):
        """
        Initialize the SWGOH API client.

        Args:
            api_key: API key for authentication
            discord_id: Discord user ID for authentication
            use_hmac: Whether to use HMAC authentication (required for multi-user)
        """
        self.api_key = api_key
        self.discord_id = discord_id
        self.use_hmac = use_hmac
        self.session = requests.Session()

    def _generate_hmac_signature(self, method: str, path: str, payload: dict) -> dict:
        """
        Generate HMAC signature for API authentication.

        Args:
            method: HTTP method (uppercase)
            path: API path (lowercase, e.g., '/twlogs')
            payload: Request payload dictionary

        Returns:
            Dictionary containing HMAC authentication headers
        """
        req_time = str(int(time.time() * 1000))
        hmac_obj = hmac.new(key=self.api_key.encode(), digestmod=hashlib.sha256)

        # Add timestamp
        hmac_obj.update(req_time.encode())

        # Add method (uppercase)
        hmac_obj.update(method.upper().encode())

        # Add path (lowercase)
        hmac_obj.update(path.lower().encode())

        # Add MD5 hash of payload
        payload_str = json.dumps(payload, separators=(',', ':'))
        payload_hash = hashlib.md5(payload_str.encode()).hexdigest()
        hmac_obj.update(payload_hash.encode())

        return {
            "x-timestamp": req_time,
            "Authorization": hmac_obj.hexdigest()
        }

    def _make_request(self, endpoint: str, payload_data: dict) -> requests.Response:
        """
        Make an API request with proper headers and authentication.

        Args:
            endpoint: API endpoint path (e.g., '/twlogs')
            payload_data: Request payload data (will be wrapped in {"payload": ...})

        Returns:
            Response object from the API

        Raises:
            requests.RequestException: If the request fails
        """
        # Wrap payload in required format
        payload = {"payload": payload_data}

        headers = {
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip,deflate",
            "x-discord-id": self.discord_id,
        }

        # Add authentication
        if self.use_hmac:
            headers.update(self._generate_hmac_signature("POST", endpoint, payload))
        else:
            headers["api-key"] = self.api_key

        url = f"{self.BASE_URL}{self.API_ENDPOINT}{endpoint}"

        logger.info(f"Making POST request to {url}")
        logger.debug(f"Payload: {payload}")

        try:
            response = self.session.post(
                url=url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

    def get_tw_logs(self, ally_code: str, enums: bool = False) -> Dict[str, Any]:
        """
        Get Territory War logs (attack/deployment/hold records).

        Args:
            ally_code: Player ally code (e.g., "859194332")
            enums: Whether to return enum values

        Returns:
            Dictionary containing TW logs data
        """
        payload_data = {
            "allyCode": ally_code,
            "enums": enums
        }

        response = self._make_request("/twlogs", payload_data)

        logger.info(f"Response status: {response.status_code}")

        try:
            data = response.json()
            logger.info("Successfully retrieved TW logs")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response.text}")
            raise

    def get_player(self, ally_code: str, enums: bool = False) -> Dict[str, Any]:
        """
        Get player profile, roster, and datacrons.

        Args:
            ally_code: Player ally code
            enums: Whether to return enum values

        Returns:
            Dictionary containing player data
        """
        payload_data = {
            "allyCode": ally_code,
            "enums": enums
        }

        response = self._make_request("/player", payload_data)
        return response.json()

    def get_guild(self, guild_id: str, enums: bool = False) -> Dict[str, Any]:
        """
        Get guild profile, members, and raid results.

        Args:
            guild_id: Guild ID
            enums: Whether to return enum values

        Returns:
            Dictionary containing guild data
        """
        payload_data = {
            "guildId": guild_id,
            "enums": enums
        }

        response = self._make_request("/guild", payload_data)

        logger.info(f"Response status: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        logger.debug(f"Response content length: {len(response.content)}")

        try:
            data = response.json()
            logger.info("Successfully retrieved guild data")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text (first 500 chars): {response.text[:500]}")
            logger.error(f"Response content-type: {response.headers.get('content-type')}")
            raise

    def get_guild_players(self, guild_id: str) -> List[Dict[str, Any]]:
        """
        Get a list of players from a guild with their ally codes and names.

        Args:
            guild_id: Guild ID

        Returns:
            List of dictionaries containing player information (playerId, playerName, galacticPower, etc.)
        """
        guild_data = self.get_guild(guild_id)

        logger.debug(f"Guild data keys: {guild_data.keys()}")

        # Extract member list from guild response
        # The structure might be different than expected, let's handle both cases
        events = guild_data.get('events', [])

        if not events:
            logger.error("No events found in guild data")
            logger.debug(f"Guild data structure: {list(guild_data.keys())}")
            return []

        # Get first event
        event = events[0] if isinstance(events, list) else events
        guild_info = event.get('guild', {})
        members = guild_info.get('member', [])

        logger.info(f"Found {len(members)} players in guild")

        # Extract relevant player info
        players = []
        for member in members:
            player_info = {
                'allyCode': member.get('playerId', ''),
                'playerName': member.get('playerName', ''),
                'galacticPower': member.get('galacticPower', 0),
                'characterGalacticPower': member.get('characterGalacticPower', 0),
                'shipGalacticPower': member.get('shipGalacticPower', 0),
                'playerLevel': member.get('playerLevel', 0),
                'memberLevel': member.get('memberLevel', 0),
                'guildJoinTime': member.get('guildJoinTime', 0),
                'lastActivityTime': member.get('lastActivityTime', 0),
            }
            players.append(player_info)

        # Sort by galactic power (descending)
        players.sort(key=lambda x: x['galacticPower'], reverse=True)

        return players


def analyze_tw_logs(file_path: str, our_guild_id: str = 'BQ4f8IJyRma4IWSSCurp4Q', our_guild_name: str = None, client: 'SWGOHAPIClient' = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, str]:
    """
    Analyze TW logs from a JSON file and extract player statistics.

    Args:
        file_path: Path to the TW logs JSON file
        our_guild_id: Our guild ID to filter attacks (default: BQ4f8IJyRma4IWSSCurp4Q)
        our_guild_name: Optional guild name (will be fetched from API if client provided and name not specified)
        client: Optional SWGOHAPIClient instance to fetch guild name from API

    Returns:
        Tuple of (our_attacks_df, opponent_attacks_df, our_defeats_df, opponent_defeats_df, our_guild_name, opponent_guild_name)
    """
    logger.info(f"Loading TW logs from {file_path}")
    logger.info(f"Our guild ID: {our_guild_id}")

    # Load JSON file
    with open(file_path, 'r') as f:
        content = f.read()

    # Remove the header text if present (e.g., "TWLOGS Data:\n====...")
    if content.startswith('TWLOGS') or content.startswith('\n'):
        # Find the first '{' which starts the JSON
        json_start = content.find('{')
        if json_start > 0:
            content = content[json_start:]

    data = json.loads(content)

    # Extract the events array
    events = data.get('data', [])
    logger.info(f"Found {len(events)} total events")

    # Parse successful attacks
    our_attacks = []
    opponent_attacks = []

    for event in events:
        # Check if this is a successful attack
        activity_key = event.get('payload', {}).get('zoneData', {}).get('activityLogMessage', {}).get('key', '')

        if activity_key == 'TERRITORY_CHANNEL_ACTIVITY_CONFLICT_SQUAD_WIN':
            war_squad = event.get('payload', {}).get('warSquad', {})
            info = event.get('info', {})
            zone_data = event.get('payload', {}).get('zoneData', {})

            # Extract banner count from params
            params = zone_data.get('activityLogMessage', {}).get('param', [])
            banners = 0
            if params and len(params) > 0:
                param_values = params[0].get('paramValue', [])
                if param_values:
                    try:
                        banners = int(param_values[0])
                    except (ValueError, IndexError):
                        banners = 0

            # Get the guild ID from zone data
            event_guild_id = zone_data.get('guildId', '')

            # IMPORTANT: In SQUAD_WIN events:
            # - info.authorName = ATTACKER (who won the battle)
            # - warSquad.playerName = DEFENDER (who was defeated)
            attack_data = {
                'attacker_id': info.get('authorId', ''),
                'attacker_name': info.get('authorName', ''),
                'defender_id': war_squad.get('playerId', ''),
                'defender_name': war_squad.get('playerName', ''),
                'banners': banners,
                'squad_power': war_squad.get('power', 0),
                'zone_id': zone_data.get('zoneId', ''),
                'timestamp': int(info.get('timestamp', 0)),
                'guild_id': event_guild_id,
            }

            # Separate our attacks from opponent attacks based on guild ID
            # Note: guildId in zoneData is the ATTACKING guild's ID (not defending!)
            # So if zoneData.guildId == our_guild_id, it means WE are attacking
            # And if zoneData.guildId != our_guild_id, it means OPPONENT is attacking
            if event_guild_id == our_guild_id:
                # This is an attack BY our guild
                our_attacks.append(attack_data)
            else:
                # This is an attack BY opponent guild
                opponent_attacks.append(attack_data)

    logger.info(f"Found {len(our_attacks)} attacks by our guild")
    logger.info(f"Found {len(opponent_attacks)} attacks by opponent guild")

    # Create DataFrames
    our_df = pd.DataFrame(our_attacks)
    opponent_df = pd.DataFrame(opponent_attacks)

    # Add defeat tracking: count how many times each player was defeated
    if not our_df.empty and not opponent_df.empty:
        # Count defeats for our guild (when they appear as defenders in opponent's attacks)
        our_defeats = opponent_df.groupby(['defender_id', 'defender_name']).size().reset_index(name='defeats')
        our_defeats.columns = ['attacker_id', 'attacker_name', 'defeats']

        # Count defeats for opponent guild (when they appear as defenders in our attacks)
        opponent_defeats = our_df.groupby(['defender_id', 'defender_name']).size().reset_index(name='defeats')
        opponent_defeats.columns = ['attacker_id', 'attacker_name', 'defeats']
    else:
        our_defeats = pd.DataFrame(columns=['attacker_id', 'attacker_name', 'defeats'])
        opponent_defeats = pd.DataFrame(columns=['attacker_id', 'attacker_name', 'defeats'])

    if our_df.empty:
        logger.warning("No attacks found for our guild")
    if opponent_df.empty:
        logger.warning("No attacks found for opponent guild")

    # Extract guild names from the data if not provided
    if our_guild_name is None:
        # Try to fetch from API if client is provided
        if client:
            try:
                logger.info("Fetching guild name from API...")
                guild_data = client.get_guild(our_guild_id)
                our_guild_name = guild_data.get('events', {}).get('guild', {}).get('name', 'DarthJedii56')
                logger.info(f"Retrieved guild name: {our_guild_name}")
            except Exception as e:
                logger.warning(f"Could not fetch guild name from API: {e}")
                our_guild_name = "DarthJedii56"
        else:
            our_guild_name = "DarthJedii56"

    # Get opponent guild name from most common attacker in opponent attacks
    opponent_guild_name = "Opponent Guild"

    return our_df, opponent_df, our_defeats, opponent_defeats, our_guild_name, opponent_guild_name


def get_attack_summary(df: pd.DataFrame, defeats_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate summary statistics per player from attack data.

    Args:
        df: DataFrame with individual attack records
        defeats_df: DataFrame with defeat counts per player

    Returns:
        DataFrame with aggregated player statistics including wins/total
    """
    if df.empty:
        return pd.DataFrame()

    # Group by attacker and calculate stats
    summary = df.groupby(['attacker_id', 'attacker_name']).agg({
        'banners': ['count', 'sum', 'mean'],
        'squad_power': 'mean'
    }).round(2)

    # Flatten column names
    summary.columns = ['wins', 'total_banners', 'avg_banners', 'avg_squad_power']
    summary = summary.reset_index()

    # Add defeat counts
    if not defeats_df.empty:
        summary = summary.merge(
            defeats_df,
            on=['attacker_id', 'attacker_name'],
            how='left'
        )
        # Fill NaN defeats with 0
        summary['defeats'] = summary['defeats'].fillna(0).astype(int)
    else:
        summary['defeats'] = 0

    # Calculate total attacks (wins + defeats)
    summary['total_attacks'] = summary['wins'] + summary['defeats']

    # Create wins/total display column
    summary['attacks'] = summary.apply(
        lambda row: f"{int(row['wins'])}/{int(row['total_attacks'])}" if row['total_attacks'] > row['wins']
        else str(int(row['wins'])),
        axis=1
    )

    # Reorder columns
    summary = summary[['attacker_id', 'attacker_name', 'attacks', 'total_banners', 'avg_banners', 'avg_squad_power']]

    # Sort by total banners descending
    summary = summary.sort_values('total_banners', ascending=False)

    return summary


def load_config_from_env() -> tuple[Optional[str], Optional[str]]:
    """
    Load configuration from environment variables.

    Returns:
        Tuple of (api_key, discord_id) or (None, None) if not found
    """
    api_key = os.getenv('SWGOH_API_KEY')
    discord_id = os.getenv('SWGOH_DISCORD_ID')
    return api_key, discord_id


def main():
    """Main entry point for the SWGOH API client."""
    parser = argparse.ArgumentParser(
        description='SWGOH API Client - Query data from Mhanndalorian Bot'
    )
    parser.add_argument(
        '--menu',
        action='store_true',
        help='Launch interactive menu system (default if no other arguments provided)'
    )
    parser.add_argument(
        '--api-key',
        help='API key for authentication (or set SWGOH_API_KEY env var)'
    )
    parser.add_argument(
        '--discord-id',
        help='Discord user ID for authentication (or set SWGOH_DISCORD_ID env var)'
    )
    parser.add_argument(
        '--ally-code',
        default='657146191',
        help='Player ally code to query (default: 657146191)'
    )
    parser.add_argument(
        '--endpoint',
        default='twlogs',
        choices=['twlogs', 'player', 'guild', 'guild-players', 'analyze-tw', 'leader-stats', 'defense-stats', 'participation', 'ai-query', 'ai-chat'],
        help='API endpoint to query (default: twlogs)'
    )
    parser.add_argument(
        '--guild-id',
        default='BQ4f8IJyRma4IWSSCurp4Q',
        help='Guild ID (default: BQ4f8IJyRma4IWSSCurp4Q)'
    )
    parser.add_argument(
        '--list-players',
        action='store_true',
        help='When using guild endpoint, output just the player list'
    )
    parser.add_argument(
        '--enums',
        action='store_true',
        help='Return enum values in response'
    )
    parser.add_argument(
        '--use-hmac',
        action='store_true',
        help='Use HMAC authentication (required for multi-user access)'
    )
    parser.add_argument(
        '--input-file',
        help='Input file for analysis (required for analyze-tw endpoint)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as formatted JSON'
    )
    parser.add_argument(
        '--output', '-o',
        help='Write output to file instead of stdout'
    )
    parser.add_argument(
        '--ai-query',
        help='Natural language query for AI analysis (required for ai-query endpoint)'
    )
    parser.add_argument(
        '--ai-provider',
        default=os.getenv('DEFAULT_AI_PROVIDER', 'openai'),
        choices=['openai', 'anthropic', 'google'],
        help='AI provider to use (default: openai, or from DEFAULT_AI_PROVIDER env var)'
    )
    parser.add_argument(
        '--ai-model',
        help='AI model to use (gpt-4o-mini/gpt-4o for OpenAI, sonnet/opus/haiku for Anthropic, pro/flash for Google). Uses provider defaults if not specified.'
    )
    parser.add_argument(
        '--detail',
        action='store_true',
        help='Show detailed per-player squad statistics (for leader-stats endpoint)'
    )

    args = parser.parse_args()

    # If no arguments provided (except defaults), launch menu system
    # Check if any non-default arguments were provided
    provided_args = [arg for arg in sys.argv[1:] if not arg.startswith('-')]
    has_explicit_args = len(sys.argv) > 1 and (
        args.menu or
        args.input_file or
        args.ai_query or
        args.endpoint != 'twlogs' or
        args.output or
        args.list_players or
        args.detail
    )

    # Launch menu system if --menu flag or no explicit arguments
    if args.menu or not has_explicit_args:
        from swgoh_menu import main as menu_main
        menu_main()
        return

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Get credentials
    api_key = args.api_key
    discord_id = args.discord_id

    # Try loading from environment if not provided
    if not api_key or not discord_id:
        env_api_key, env_discord_id = load_config_from_env()
        api_key = api_key or env_api_key
        discord_id = discord_id or env_discord_id

    # Handle analyze-tw endpoint separately
    if args.endpoint == 'analyze-tw':
        if not args.input_file:
            logger.error("--input-file is required for analyze-tw endpoint")
            sys.exit(1)

        try:
            # Create client if we have credentials (to fetch guild name)
            client = None
            if api_key and discord_id:
                client = SWGOHAPIClient(api_key, discord_id, use_hmac=args.use_hmac)
                logger.info("API credentials found - will fetch guild name from API")
            else:
                logger.info("No API credentials - using default guild name")

            # Analyze TW logs
            our_df, opponent_df, our_defeats, opponent_defeats, our_guild_name, opponent_guild_name = analyze_tw_logs(
                args.input_file, args.guild_id, None, client
            )
            our_summary = get_attack_summary(our_df, our_defeats)
            opponent_summary = get_attack_summary(opponent_df, opponent_defeats)

            # Format output
            if args.json:
                output = json.dumps({
                    'our_guild': {
                        'name': our_guild_name,
                        'attacks': json.loads(our_summary.to_json(orient='records'))
                    },
                    'opponent_guild': {
                        'name': opponent_guild_name,
                        'attacks': json.loads(opponent_summary.to_json(orient='records'))
                    }
                }, indent=2)
            else:
                output = "\n" + "=" * 80 + "\n"
                output += f"TERRITORY WAR ATTACK SUMMARY - {our_guild_name.upper()}\n"
                output += "=" * 80 + "\n"
                output += f"\nTotal Attacks: {len(our_df)}\n"
                if not our_df.empty:
                    output += f"Unique Players: {our_summary['attacker_name'].nunique()}\n"
                    output += f"Total Banners: {our_summary['total_banners'].sum():.0f}\n\n"
                    output += our_summary.to_string(index=False)
                else:
                    output += "No attacks found for our guild.\n"

                output += "\n\n" + "=" * 80 + "\n"
                output += f"TERRITORY WAR ATTACK SUMMARY - {opponent_guild_name.upper()}\n"
                output += "=" * 80 + "\n"
                output += f"\nTotal Attacks: {len(opponent_df)}\n"
                if not opponent_df.empty:
                    output += f"Unique Players: {opponent_summary['attacker_name'].nunique()}\n"
                    output += f"Total Banners: {opponent_summary['total_banners'].sum():.0f}\n\n"
                    output += opponent_summary.to_string(index=False)
                else:
                    output += "No attacks found for opponent guild.\n"

            # Write to file or stdout
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(output)
                logger.info(f"Output written to {args.output}")
            else:
                print(output)

        except Exception as e:
            logger.error(f"Error analyzing TW logs: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

        return

    # Handle leader-stats endpoint
    if args.endpoint == 'leader-stats':
        if not args.input_file:
            logger.error("--input-file is required for leader-stats endpoint")
            sys.exit(1)

        try:
            from swgoh_data_context import SWGOHDataContext

            # Load TW data
            context = SWGOHDataContext(guild_id=args.guild_id)
            if not context.load_tw_logs(args.input_file):
                logger.error(f"Failed to load TW logs from {args.input_file}")
                sys.exit(1)

            # Get summary with leader stats
            summary = context.get_tw_summary()
            leaders_we_faced = summary.get('defending_leaders_we_faced', [])
            our_defending_leaders = summary.get('our_defending_leaders', [])

            output = ""

            # Table 1: Leaders we faced when attacking
            if leaders_we_faced:
                output += "\n" + "=" * 120 + "\n"
                output += "ENEMY DEFENDING LEADERS - WHO WE ATTACKED (Sorted by Hold Rate)\n"
                output += "=" * 140 + "\n\n"
                output += f"Guild: {summary.get('guild_name', 'Unknown')}\n"
                output += f"Our Total Attacks: {summary.get('total_attacks', 0)}\n\n"

                # Table header
                output += f"{'Leader':<30} | {'Attempts':>8} | {'Wins':>5} | {'Holds':>5} | {'Win Rate':>8} | {'Hold Rate':>9} | {'Avg Banners':>12}\n"
                output += "-" * 120 + "\n"

                # Table rows
                for leader in leaders_we_faced:
                    output += (
                        f"{leader['leader']:<30} | "
                        f"{leader['total_attempts']:>8} | "
                        f"{leader['wins']:>5} | "
                        f"{leader['holds']:>5} | "
                        f"{leader['win_rate']:>7.1f}% | "
                        f"{leader['hold_rate']:>8.1f}% | "
                        f"{leader['avg_banners_on_wins']:>12.1f}\n"
                    )

                output += "\n" + "=" * 120 + "\n"
                output += "Note: Higher hold rate = we struggled more against this leader\n"
                output += "      Holds = defense held (failed attacks and forfeits combined)\n"
                output += "      Avg Banners shown is only for attacks we won\n\n"
            else:
                output += "No data on enemy defending leaders.\n\n"

            # Table 2: Our leaders that opponent attacked
            if our_defending_leaders:
                output += "\n" + "=" * 120 + "\n"
                output += "OUR DEFENDING LEADERS - WHO OPPONENT ATTACKED (Sorted by Hold Rate)\n"
                output += "=" * 120 + "\n\n"
                opponent_stats = summary.get('opponent_stats', {})
                output += f"Opponent Total Attacks (on us): {opponent_stats.get('total_attacks', 0)}\n\n"

                # Table header
                output += f"{'Leader':<30} | {'Attempts':>8} | {'Wins':>5} | {'Holds':>5} | {'Win Rate':>8} | {'Hold Rate':>9} | {'Avg Banners':>12}\n"
                output += "-" * 120 + "\n"

                # Table rows
                for leader in our_defending_leaders:
                    output += (
                        f"{leader['leader']:<30} | "
                        f"{leader['total_attempts']:>8} | "
                        f"{leader['wins']:>5} | "
                        f"{leader['holds']:>5} | "
                        f"{leader['win_rate']:>7.1f}% | "
                        f"{leader['hold_rate']:>8.1f}% | "
                        f"{leader['avg_banners_on_wins']:>12.1f}\n"
                    )

                output += "\n" + "=" * 120 + "\n"
                output += "Note: Higher hold rate = our defense held better (GOOD for us!)\n"
                output += "      Holds = defense held (opponent's failed attacks and forfeits combined)\n"
                output += "      Avg Banners shown is what opponent earned when they won\n"
            else:
                output += "No data on our defending leaders.\n"

            # Detailed breakdown if --detail flag is set
            if args.detail:
                detailed_enemy = summary.get('detailed_enemy_squads', [])
                detailed_ours = summary.get('detailed_our_squads', [])

                # Detailed enemy squads
                if detailed_enemy:
                    output += "\n\n" + "=" * 140 + "\n"
                    output += "DETAILED ENEMY DEFENDING SQUADS - BY PLAYER & LEADER (Sorted by Hold Rate)\n"
                    output += "=" * 140 + "\n\n"

                    # Table header
                    output += f"{'Player Name':<25} | {'Leader':<30} | {'Attempts':>8} | {'Wins':>5} | {'Holds':>5} | {'Win Rate':>8} | {'Hold Rate':>9} | {'Avg Banners':>12}\n"
                    output += "-" * 140 + "\n"

                    # Table rows
                    for squad in detailed_enemy:
                        output += (
                            f"{squad['defender_name']:<25} | "
                            f"{squad['leader']:<30} | "
                            f"{squad['total_attempts']:>8} | "
                            f"{squad['wins']:>5} | "
                            f"{squad['holds']:>5} | "
                            f"{squad['win_rate']:>7.1f}% | "
                            f"{squad['hold_rate']:>8.1f}% | "
                            f"{squad['avg_banners_on_wins']:>12.1f}\n"
                        )

                    output += "\n"

                # Detailed our squads
                if detailed_ours:
                    output += "\n" + "=" * 140 + "\n"
                    output += "DETAILED OUR DEFENDING SQUADS - BY PLAYER & LEADER (Sorted by Hold Rate)\n"
                    output += "=" * 140 + "\n\n"

                    # Table header
                    output += f"{'Player Name':<25} | {'Leader':<30} | {'Attempts':>8} | {'Wins':>5} | {'Holds':>5} | {'Win Rate':>8} | {'Hold Rate':>9} | {'Avg Banners':>12}\n"
                    output += "-" * 140 + "\n"

                    # Table rows
                    for squad in detailed_ours:
                        output += (
                            f"{squad['defender_name']:<25} | "
                            f"{squad['leader']:<30} | "
                            f"{squad['total_attempts']:>8} | "
                            f"{squad['wins']:>5} | "
                            f"{squad['holds']:>5} | "
                            f"{squad['win_rate']:>7.1f}% | "
                            f"{squad['hold_rate']:>8.1f}% | "
                            f"{squad['avg_banners_on_wins']:>12.1f}\n"
                        )

                    output += "\n"

            # Write to file or stdout
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(output)
                logger.info(f"Output written to {args.output}")
            else:
                print(output)

        except Exception as e:
            logger.error(f"Error generating leader stats: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

        return

    # Handle defense-stats endpoint
    if args.endpoint == 'defense-stats':
        if not args.input_file:
            logger.error("--input-file is required for defense-stats endpoint")
            sys.exit(1)

        try:
            from swgoh_data_context import SWGOHDataContext

            # Load TW data
            context = SWGOHDataContext(guild_id=args.guild_id)
            if not context.load_tw_logs(args.input_file):
                logger.error("Failed to load TW logs")
                sys.exit(1)

            # Get summary with defense contributor stats
            summary = context.get_tw_summary()
            defense_contributors = summary.get('defense_contributors', [])

            # Build output
            output = "\n" + "=" * 140 + "\n"
            output += "DEFENSE CONTRIBUTORS - WHO DEPLOYED AND HOW THEY PERFORMED\n"
            output += "=" * 140 + "\n\n"

            if defense_contributors:
                output += f"Total Players Who Deployed: {len(defense_contributors)}\n"
                output += f"Total Squads Deployed: {sum(d['squads_deployed'] for d in defense_contributors)}\n\n"

                # Table header
                output += f"{'Player Name':<25} | {'Squads':>6} | {'Avg Power':>9} | {'Attempts':>8} | {'Wins':>5} | {'Holds':>5} | {'Hold Rate':>9} | {'Banners Lost':>12}\n"
                output += "-" * 140 + "\n"

                # Table rows
                for defender in defense_contributors[:20]:  # Top 20
                    output += (
                        f"{defender['player_name']:<25} | "
                        f"{defender['squads_deployed']:>6} | "
                        f"{defender['avg_squad_power']:>9,.0f} | "
                        f"{defender['total_attempts']:>8} | "
                        f"{defender['wins']:>5} | "
                        f"{defender['holds']:>5} | "
                        f"{defender['hold_rate']:>8.1f}% | "
                        f"{defender['banners_given_up']:>12}\n"
                    )

                output += "\n" + "=" * 140 + "\n"
                output += "Note: Sorted by total holds (most valuable defenders first)\n"
                output += "      Holds = defense held (opponent's failed attacks and forfeits)\n"
                output += "      Banners Lost = total banners opponent earned when they won\n"
                output += "      Players with 0 attempts had squads that were never attacked\n"
            else:
                output += "No defense deployment data found.\n"

            # Write to file or stdout
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(output)
                logger.info(f"Output written to {args.output}")
            else:
                print(output)

        except Exception as e:
            logger.error(f"Error generating defense stats: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

        return

    # Handle participation endpoint
    if args.endpoint == 'participation':
        if not args.input_file:
            logger.error("--input-file is required for participation endpoint")
            sys.exit(1)

        try:
            from swgoh_data_context import SWGOHDataContext

            # Load TW data
            context = SWGOHDataContext(guild_id=args.guild_id)
            if not context.load_tw_logs(args.input_file):
                logger.error("Failed to load TW logs")
                sys.exit(1)

            # Try to load guild data to get complete roster
            # This allows us to identify players who signed up but didn't participate at all
            guild_loaded = False
            if api_key and discord_id:
                # Fetch guild data to get roster
                try:
                    client = SWGOHAPIClient(api_key, discord_id, use_hmac=args.use_hmac)
                    guild_data = client.get_guild(args.guild_id)
                    if guild_data and guild_data.get('code') == 0:
                        # Save temporarily and load
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                            json.dump(guild_data, tmp)
                            tmp_path = tmp.name

                        if context.load_guild_data(tmp_path):
                            guild_loaded = True
                            logger.info("Guild roster loaded successfully")

                        # Clean up temp file
                        os.unlink(tmp_path)
                except Exception as e:
                    logger.warning(f"Could not load guild data: {e}")
            else:
                logger.info("No API credentials - skipping guild roster fetch")

            # Get participation report (50 banners minimum by default)
            # Will automatically use guild roster if loaded
            report = context.get_participation_report(min_banners=50, min_attacks=1)

            # Build output
            output = "\n" + "=" * 140 + "\n"
            output += "PARTICIPATION REPORT\n"
            output += "=" * 140 + "\n\n"

            if guild_loaded:
                output += "✓ Guild roster loaded - includes complete non-participants\n\n"
            else:
                output += "⚠ Guild roster not loaded - non-participants limited to TW log data only\n\n"

            output += f"Total Players: {report['total_players']}\n"
            output += f"Players Who Attacked: {report['players_who_attacked']}\n"
            output += f"Players Who Deployed Defense: {report['players_who_defended']}\n"
            output += f"Minimum Banners Threshold: {report['min_banners_threshold']}\n\n"

            # Underperformers section
            underperformers = report.get('underperformers', [])
            if underperformers:
                output += "=" * 140 + "\n"
                output += f"UNDERPERFORMERS - Attacked but earned less than {report['min_banners_threshold']} banners\n"
                output += "=" * 140 + "\n\n"

                output += f"{'Player Name':<25} | {'Attacks':>7} | {'Wins':>5} | {'Off Banners':>11} | {'Def Banners':>11} | {'Total':>7} | {'Squads':>6} | {'Holds':>5}\n"
                output += "-" * 140 + "\n"

                for player in underperformers:
                    output += (
                        f"{player['player_name']:<25} | "
                        f"{player['attacks']:>7} | "
                        f"{player['wins']:>5} | "
                        f"{player['offensive_banners']:>11} | "
                        f"{player['defensive_banners']:>11} | "
                        f"{player['total_banners']:>7} | "
                        f"{player['squads_deployed']:>6} | "
                        f"{player['defensive_holds']:>5}\n"
                    )
                output += "\n"
            else:
                output += f"✓ No underperformers - all attacking players earned at least {report['min_banners_threshold']} banners!\n\n"

            # Non-participants section
            non_participants = report.get('non_participants', [])
            if non_participants:
                output += "=" * 140 + "\n"
                output += "NON-PARTICIPANTS - Did not attack or deploy defense\n"
                output += "=" * 140 + "\n\n"

                for player in non_participants:
                    output += f"  - {player['player_name']}\n"
                output += "\n"
            else:
                output += "✓ No non-participants - everyone participated!\n\n"

            # Full participation table
            output += "=" * 140 + "\n"
            output += "FULL PARTICIPATION TABLE (sorted by banners)\n"
            output += "=" * 140 + "\n\n"

            output += f"{'Player Name':<25} | {'Attacks':>7} | {'Wins':>5} | {'Off Banners':>11} | {'Def Banners':>11} | {'Total':>7} | {'Squads':>6} | {'Holds':>5}\n"
            output += "-" * 140 + "\n"

            for player in report.get('all_participants', []):
                output += (
                    f"{player['player_name']:<25} | "
                    f"{player['attacks']:>7} | "
                    f"{player['wins']:>5} | "
                    f"{player['offensive_banners']:>11} | "
                    f"{player['defensive_banners']:>11} | "
                    f"{player['total_banners']:>7} | "
                    f"{player['squads_deployed']:>6} | "
                    f"{player['defensive_holds']:>5}\n"
                )

            output += "\n" + "=" * 140 + "\n"
            output += f"Note: Underperformers are players who attacked but earned less than {report['min_banners_threshold']} banners\n"
            output += "      This may indicate inefficient attacks or weak squads\n"

            # Write to file or stdout
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(output)
                logger.info(f"Output written to {args.output}")
            else:
                print(output)

        except Exception as e:
            logger.error(f"Error generating participation report: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

        return

    # Handle ai-query endpoint
    if args.endpoint == 'ai-query':
        if not args.input_file:
            logger.error("--input-file is required for ai-query endpoint")
            sys.exit(1)
        if not args.ai_query:
            logger.error("--ai-query is required for ai-query endpoint")
            sys.exit(1)

        try:
            from swgoh_ai_analyzer import create_analyzer

            logger.info(f"Creating AI analyzer with provider: {args.ai_provider}")
            analyzer = create_analyzer(
                data_file=args.input_file,
                provider=args.ai_provider,
                model=args.ai_model,
                guild_id=args.guild_id
            )

            logger.info(f"Running query: {args.ai_query}")
            response = analyzer.query(args.ai_query)

            # Format output
            output = "\n" + "=" * 80 + "\n"
            output += "AI ANALYSIS\n"
            output += "=" * 80 + "\n"
            output += f"Query: {args.ai_query}\n"
            output += f"Provider: {args.ai_provider}\n"
            output += "=" * 80 + "\n\n"
            output += response + "\n"

            # Write to file or stdout
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(output)
                logger.info(f"Output written to {args.output}")
            else:
                print(output)

        except Exception as e:
            logger.error(f"Error running AI query: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

        return

    # Handle ai-chat endpoint
    if args.endpoint == 'ai-chat':
        if not args.input_file:
            logger.error("--input-file is required for ai-chat endpoint")
            sys.exit(1)

        try:
            from swgoh_ai_analyzer import create_analyzer

            logger.info(f"Creating AI analyzer with provider: {args.ai_provider}")
            analyzer = create_analyzer(
                data_file=args.input_file,
                provider=args.ai_provider,
                model=args.ai_model,
                guild_id=args.guild_id
            )

            print("\n" + "=" * 80)
            print("SWGOH AI CHAT - Interactive Analysis Mode")
            print("=" * 80)
            print(f"Provider: {args.ai_provider}")
            print(f"Data file: {args.input_file}")
            print("\nType your questions about the TW data. Special commands:")
            print("  /clear    - Clear conversation history")
            print("  /history  - Show conversation history")
            print("  /export   - Export conversation to file")
            print("  /quit     - Exit chat mode")
            print("=" * 80 + "\n")

            # Interactive loop
            while True:
                try:
                    user_input = input("You: ").strip()

                    if not user_input:
                        continue

                    # Handle special commands
                    if user_input.lower() == '/quit':
                        print("\nExiting chat mode. Goodbye!")
                        break
                    elif user_input.lower() == '/clear':
                        analyzer.clear_history()
                        print("✓ Conversation history cleared.\n")
                        continue
                    elif user_input.lower() == '/history':
                        history = analyzer.get_history()
                        if not history:
                            print("No conversation history yet.\n")
                        else:
                            print("\n--- Conversation History ---")
                            for i, msg in enumerate(history, 1):
                                role = "You" if msg['role'] == 'user' else "AI"
                                print(f"\n[{i}] {role}: {msg['content']}")
                            print("\n--- End History ---\n")
                        continue
                    elif user_input.lower().startswith('/export'):
                        parts = user_input.split(maxsplit=1)
                        filename = parts[1] if len(parts) > 1 else 'conversation.json'
                        analyzer.export_conversation(filename)
                        print(f"✓ Conversation exported to {filename}\n")
                        continue

                    # Regular chat message
                    response = analyzer.chat(user_input)
                    print(f"\nAI: {response}\n")

                except KeyboardInterrupt:
                    print("\n\nExiting chat mode. Goodbye!")
                    break
                except EOFError:
                    print("\n\nExiting chat mode. Goodbye!")
                    break
                except Exception as e:
                    logger.error(f"Error in chat: {e}")
                    if args.verbose:
                        import traceback
                        traceback.print_exc()
                    print(f"\nError: {e}\n")

        except Exception as e:
            logger.error(f"Error starting AI chat: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

        return

    # Validate credentials for API endpoints
    if not api_key or not discord_id:
        logger.error("API key and Discord ID are required")
        logger.error("Provide them via --api-key and --discord-id or set SWGOH_API_KEY and SWGOH_DISCORD_ID environment variables")
        sys.exit(1)

    # No need to validate ally-code anymore since it has a default

    # Create client and make request
    try:
        client = SWGOHAPIClient(api_key, discord_id, use_hmac=args.use_hmac)

        # Call appropriate endpoint
        if args.endpoint == 'twlogs':
            results = client.get_tw_logs(args.ally_code, enums=args.enums)
        elif args.endpoint == 'player':
            results = client.get_player(args.ally_code, enums=args.enums)
        elif args.endpoint == 'guild':
            results = client.get_guild(args.guild_id, enums=args.enums)
            # If --list-players flag is set, extract just the player list
            if args.list_players:
                members = results.get('events', [{}])[0].get('guild', {}).get('member', [])
                results = [{
                    'allyCode': m.get('playerId', ''),
                    'playerName': m.get('playerName', ''),
                    'galacticPower': m.get('galacticPower', 0)
                } for m in members]
        elif args.endpoint == 'guild-players':
            results = client.get_guild_players(args.guild_id)

        # Format output
        if args.json:
            output = json.dumps(results, indent=2)
        else:
            output = f"\n{args.endpoint.upper()} Data:\n" + "=" * 80 + "\n"
            output += json.dumps(results, indent=2)

        # Write to file or stdout
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            logger.info(f"Output written to {args.output}")
        else:
            print(output)

    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
