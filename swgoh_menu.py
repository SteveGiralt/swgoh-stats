#!/usr/bin/env python3
"""
SWGOH Menu System
Interactive menu-driven interface for SWGOH data analysis.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from swgoh_api_client import SWGOHAPIClient
from swgoh_data_context import SWGOHDataContext

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SWGOHMenu:
    """Interactive menu system for SWGOH data analysis."""

    def __init__(self):
        """Initialize the menu system."""
        self.api_key = os.getenv('SWGOH_API_KEY')
        self.discord_id = os.getenv('SWGOH_DISCORD_ID')
        self.guild_id = os.getenv('SWGOH_GUILD_ID', 'BQ4f8IJyRma4IWSSCurp4Q')
        self.ally_code = os.getenv('SWGOH_ALLY_CODE', '657146191')

        # Data directory for cached files
        self.data_dir = Path.home() / '.swgoh_data'
        self.data_dir.mkdir(exist_ok=True)

        # Data files
        self.tw_logs_file = self.data_dir / 'tw_logs.json'
        self.guild_data_file = self.data_dir / 'guild_data.json'
        self.metadata_file = self.data_dir / 'metadata.json'

        # Load metadata (timestamps, etc.)
        self.metadata = self._load_metadata()

        # API client (initialized when needed)
        self.client: Optional[SWGOHAPIClient] = None

        # Data context
        self.context: Optional[SWGOHDataContext] = None

    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load metadata: {e}")

        return {
            'tw_logs_last_refresh': None,
            'guild_roster_last_refresh': None,
        }

    def _save_metadata(self):
        """Save metadata to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    def _get_api_client(self) -> Optional[SWGOHAPIClient]:
        """Get or create API client."""
        if not self.api_key or not self.discord_id:
            print("\n❌ Error: API credentials not found!")
            print("Please set SWGOH_API_KEY and SWGOH_DISCORD_ID in your .env file")
            return None

        if not self.client:
            self.client = SWGOHAPIClient(self.api_key, self.discord_id)

        return self.client

    def _format_timestamp(self, timestamp_str: Optional[str]) -> str:
        """Format timestamp for display."""
        if not timestamp_str:
            return "Never"

        try:
            dt = datetime.fromisoformat(timestamp_str)
            return dt.strftime("%Y-%m-%d %I:%M %p")
        except Exception:
            return "Unknown"

    def _clear_screen(self):
        """Clear the terminal screen."""
        os.system('clear' if os.name != 'nt' else 'cls')

    def _wait_for_enter(self):
        """Wait for user to press enter."""
        input("\nPress Enter to continue...")

    def show_main_menu(self):
        """Display the main menu."""
        self._clear_screen()
        print("=" * 80)
        print(" " * 20 + "SWGOH DATA ANALYZER")
        print("=" * 80)
        print()

        # Show data status
        print("📊 DATA STATUS:")
        print(f"   TW Logs:      Last refreshed: {self._format_timestamp(self.metadata.get('tw_logs_last_refresh'))}")
        print(f"   Guild Roster: Last refreshed: {self._format_timestamp(self.metadata.get('guild_roster_last_refresh'))}")
        print()
        print("-" * 80)
        print()
        print("MENU OPTIONS:")
        print()
        print("  1. Refresh TW Logs")
        print("  2. Refresh Guild Roster")
        print("  3. Run Reports")
        print("  4. AI Query (Interactive)")
        print("  5. AI Chat (Conversation Mode)")
        print("  6. Settings")
        print("  0. Exit")
        print()
        print("=" * 80)

    def refresh_tw_logs(self):
        """Refresh TW logs from API."""
        print("\n📥 Refreshing TW Logs...")
        print(f"   Using ally code: {self.ally_code}")

        client = self._get_api_client()
        if not client:
            return False

        try:
            # Fetch TW logs
            data = client.get_tw_logs(self.ally_code)

            # Save to file
            with open(self.tw_logs_file, 'w') as f:
                json.dump(data, f, indent=2)

            # Update metadata
            self.metadata['tw_logs_last_refresh'] = datetime.now().isoformat()
            self._save_metadata()

            print(f"✅ TW Logs saved to: {self.tw_logs_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to refresh TW logs: {e}")
            print(f"❌ Error: {e}")
            return False

    def refresh_guild_roster(self):
        """Refresh guild roster from API."""
        print("\n📥 Refreshing Guild Roster...")
        print(f"   Using guild ID: {self.guild_id}")

        client = self._get_api_client()
        if not client:
            return False

        try:
            # Fetch guild data
            data = client.get_guild(self.guild_id)

            # Check for API error
            if data.get('code') != 0:
                error_msg = data.get('message', 'Unknown error')
                print(f"❌ API Error: {error_msg}")
                return False

            # Save to file
            with open(self.guild_data_file, 'w') as f:
                json.dump(data, f, indent=2)

            # Update metadata
            self.metadata['guild_roster_last_refresh'] = datetime.now().isoformat()
            self._save_metadata()

            # Show member count - handle both response structures
            # Structure: events -> guild -> member OR events (array) -> [0] -> guild -> member
            events = data.get('events', {})
            if isinstance(events, list) and len(events) > 0:
                guild = events[0].get('guild', {})
            elif isinstance(events, dict):
                guild = events.get('guild', {})
            else:
                guild = {}

            members = guild.get('member', [])
            print(f"✅ Guild Roster saved to: {self.guild_data_file}")
            print(f"   Found {len(members)} guild members")
            return True

        except Exception as e:
            logger.error(f"Failed to refresh guild roster: {e}", exc_info=True)
            print(f"❌ Error: {e}")
            return False

    def show_reports_menu(self):
        """Display the reports submenu."""
        while True:
            self._clear_screen()
            print("=" * 80)
            print(" " * 25 + "REPORTS MENU")
            print("=" * 80)
            print()
            print("  1. TW Attack Summary")
            print("  2. Leader Stats (Defending Leaders)")
            print("  3. Defense Stats (Defense Contributors)")
            print("  4. Participation Report")
            print("  5. All Reports (Full Analysis)")
            print("  0. Back to Main Menu")
            print()
            print("=" * 80)

            choice = input("\nSelect option: ").strip()

            if choice == '0':
                break
            elif choice == '1':
                self.run_tw_summary_report()
            elif choice == '2':
                self.run_leader_stats_report()
            elif choice == '3':
                self.run_defense_stats_report()
            elif choice == '4':
                self.run_participation_report()
            elif choice == '5':
                self.run_all_reports()
            else:
                print("Invalid option. Please try again.")
                self._wait_for_enter()

    def _ensure_tw_data_loaded(self) -> bool:
        """Ensure TW data is loaded and available."""
        if not self.tw_logs_file.exists():
            print("\n❌ No TW logs found. Please refresh TW logs first (Option 1).")
            self._wait_for_enter()
            return False

        # Load data context if needed
        if not self.context:
            self.context = SWGOHDataContext(guild_id=self.guild_id)
            if not self.context.load_tw_logs(str(self.tw_logs_file)):
                print("\n❌ Failed to load TW logs.")
                self._wait_for_enter()
                return False

            # Load guild data if available
            if self.guild_data_file.exists():
                self.context.load_guild_data(str(self.guild_data_file))

        return True

    def run_tw_summary_report(self):
        """Run TW attack summary report."""
        print("\n" + "=" * 80)
        print(" " * 20 + "TW ATTACK SUMMARY REPORT")
        print("=" * 80 + "\n")

        if not self._ensure_tw_data_loaded():
            return

        try:
            from swgoh_api_client import analyze_tw_logs, get_attack_summary

            # Analyze TW logs
            our_df, opponent_df, our_defeats, opponent_defeats, our_guild_name, opponent_guild_name = analyze_tw_logs(
                str(self.tw_logs_file), self.guild_id, None, self.client
            )
            our_summary = get_attack_summary(our_df, our_defeats)
            opponent_summary = get_attack_summary(opponent_df, opponent_defeats)

            # Display our guild
            print(f"Guild: {our_guild_name}")
            print(f"Total Attacks: {len(our_df)}")
            if not our_df.empty:
                print(f"Unique Players: {our_summary['attacker_name'].nunique()}")
                print(f"Total Banners: {our_summary['total_banners'].sum():.0f}\n")
                print(our_summary.to_string(index=False))
            else:
                print("No attacks found for our guild.\n")

            print("\n" + "=" * 80)
            print(f"Guild: {opponent_guild_name}")
            print(f"Total Attacks: {len(opponent_df)}")
            if not opponent_df.empty:
                print(f"Unique Players: {opponent_summary['attacker_name'].nunique()}")
                print(f"Total Banners: {opponent_summary['total_banners'].sum():.0f}\n")
                print(opponent_summary.to_string(index=False))
            else:
                print("No attacks found for opponent guild.\n")

        except Exception as e:
            logger.error(f"Error running TW summary: {e}")
            print(f"❌ Error: {e}")

        self._wait_for_enter()

    def run_leader_stats_report(self):
        """Run leader stats report."""
        print("\n" + "=" * 80)
        print(" " * 20 + "LEADER STATS REPORT")
        print("=" * 80 + "\n")

        if not self._ensure_tw_data_loaded():
            return

        try:
            # Ask if user wants detailed breakdown
            detail = input("Show detailed per-player stats? (y/n): ").strip().lower() == 'y'

            # Get summary with leader stats
            summary = self.context.get_tw_summary()
            leaders_we_faced = summary.get('defending_leaders_we_faced', [])
            our_defending_leaders = summary.get('our_defending_leaders', [])

            # Table 1: Leaders we faced when attacking
            if leaders_we_faced:
                print("\n" + "=" * 120)
                print("ENEMY DEFENDING LEADERS - WHO WE ATTACKED (Sorted by Hold Rate)")
                print("=" * 120 + "\n")
                print(f"Guild: {summary.get('guild_name', 'Unknown')}")
                print(f"Our Total Attacks: {summary.get('total_attacks', 0)}\n")

                print(f"{'Leader':<30} | {'Attempts':>8} | {'Wins':>5} | {'Holds':>5} | {'Win Rate':>8} | {'Hold Rate':>9} | {'Avg Banners':>12}")
                print("-" * 120)

                for leader in leaders_we_faced:
                    print(
                        f"{leader['leader']:<30} | "
                        f"{leader['total_attempts']:>8} | "
                        f"{leader['wins']:>5} | "
                        f"{leader['holds']:>5} | "
                        f"{leader['win_rate']:>7.1f}% | "
                        f"{leader['hold_rate']:>8.1f}% | "
                        f"{leader['avg_banners_on_wins']:>12.1f}"
                    )

                print("\nNote: Higher hold rate = we struggled more against this leader")

            # Table 2: Our leaders that opponent attacked
            if our_defending_leaders:
                print("\n\n" + "=" * 120)
                print("OUR DEFENDING LEADERS - WHO OPPONENT ATTACKED (Sorted by Hold Rate)")
                print("=" * 120 + "\n")
                opponent_stats = summary.get('opponent_stats', {})
                print(f"Opponent Total Attacks (on us): {opponent_stats.get('total_attacks', 0)}\n")

                print(f"{'Leader':<30} | {'Attempts':>8} | {'Wins':>5} | {'Holds':>5} | {'Win Rate':>8} | {'Hold Rate':>9} | {'Avg Banners':>12}")
                print("-" * 120)

                for leader in our_defending_leaders:
                    print(
                        f"{leader['leader']:<30} | "
                        f"{leader['total_attempts']:>8} | "
                        f"{leader['wins']:>5} | "
                        f"{leader['holds']:>5} | "
                        f"{leader['win_rate']:>7.1f}% | "
                        f"{leader['hold_rate']:>8.1f}% | "
                        f"{leader['avg_banners_on_wins']:>12.1f}"
                    )

                print("\nNote: Higher hold rate = our defense held better (GOOD for us!)")

            # Detailed breakdown if requested
            if detail:
                detailed_enemy = summary.get('detailed_enemy_squads', [])
                detailed_ours = summary.get('detailed_our_squads', [])

                if detailed_enemy:
                    print("\n\n" + "=" * 140)
                    print("DETAILED ENEMY DEFENDING SQUADS - BY PLAYER & LEADER")
                    print("=" * 140 + "\n")

                    print(f"{'Player Name':<25} | {'Leader':<30} | {'Attempts':>8} | {'Wins':>5} | {'Holds':>5} | {'Win Rate':>8} | {'Hold Rate':>9} | {'Avg Banners':>12}")
                    print("-" * 140)

                    for squad in detailed_enemy[:20]:  # Top 20
                        print(
                            f"{squad['defender_name']:<25} | "
                            f"{squad['leader']:<30} | "
                            f"{squad['total_attempts']:>8} | "
                            f"{squad['wins']:>5} | "
                            f"{squad['holds']:>5} | "
                            f"{squad['win_rate']:>7.1f}% | "
                            f"{squad['hold_rate']:>8.1f}% | "
                            f"{squad['avg_banners_on_wins']:>12.1f}"
                        )

                if detailed_ours:
                    print("\n\n" + "=" * 140)
                    print("DETAILED OUR DEFENDING SQUADS - BY PLAYER & LEADER")
                    print("=" * 140 + "\n")

                    print(f"{'Player Name':<25} | {'Leader':<30} | {'Attempts':>8} | {'Wins':>5} | {'Holds':>5} | {'Win Rate':>8} | {'Hold Rate':>9} | {'Avg Banners':>12}")
                    print("-" * 140)

                    for squad in detailed_ours[:20]:  # Top 20
                        print(
                            f"{squad['defender_name']:<25} | "
                            f"{squad['leader']:<30} | "
                            f"{squad['total_attempts']:>8} | "
                            f"{squad['wins']:>5} | "
                            f"{squad['holds']:>5} | "
                            f"{squad['win_rate']:>7.1f}% | "
                            f"{squad['hold_rate']:>8.1f}% | "
                            f"{squad['avg_banners_on_wins']:>12.1f}"
                        )

        except Exception as e:
            logger.error(f"Error running leader stats: {e}")
            print(f"❌ Error: {e}")

        self._wait_for_enter()

    def run_defense_stats_report(self):
        """Run defense stats report."""
        print("\n" + "=" * 80)
        print(" " * 20 + "DEFENSE STATS REPORT")
        print("=" * 80 + "\n")

        if not self._ensure_tw_data_loaded():
            return

        try:
            # Get summary with defense contributor stats
            summary = self.context.get_tw_summary()
            defense_contributors = summary.get('defense_contributors', [])

            if defense_contributors:
                print(f"Total Players Who Deployed: {len(defense_contributors)}")
                print(f"Total Squads Deployed: {sum(d['squads_deployed'] for d in defense_contributors)}\n")

                print(f"{'Player Name':<25} | {'Squads':>6} | {'Avg Power':>9} | {'Attempts':>8} | {'Wins':>5} | {'Holds':>5} | {'Hold Rate':>9} | {'Banners Lost':>12}")
                print("-" * 140)

                for defender in defense_contributors[:20]:  # Top 20
                    print(
                        f"{defender['player_name']:<25} | "
                        f"{defender['squads_deployed']:>6} | "
                        f"{defender['avg_squad_power']:>9,.0f} | "
                        f"{defender['total_attempts']:>8} | "
                        f"{defender['wins']:>5} | "
                        f"{defender['holds']:>5} | "
                        f"{defender['hold_rate']:>8.1f}% | "
                        f"{defender['banners_given_up']:>12}"
                    )

                print("\nNote: Sorted by total holds (most valuable defenders first)")
            else:
                print("No defense deployment data found.")

        except Exception as e:
            logger.error(f"Error running defense stats: {e}")
            print(f"❌ Error: {e}")

        self._wait_for_enter()

    def run_participation_report(self):
        """Run participation report."""
        print("\n" + "=" * 80)
        print(" " * 20 + "PARTICIPATION REPORT")
        print("=" * 80 + "\n")

        if not self._ensure_tw_data_loaded():
            return

        try:
            # Get participation report
            report = self.context.get_participation_report(min_banners=50, min_attacks=1)

            print(f"Total Players: {report['total_players']}")
            print(f"Players Who Attacked: {report['players_who_attacked']}")
            print(f"Players Who Deployed Defense: {report['players_who_defended']}")
            print(f"Minimum Banners Threshold: {report['min_banners_threshold']}\n")

            # Underperformers section
            underperformers = report.get('underperformers', [])
            if underperformers:
                print("=" * 140)
                print(f"UNDERPERFORMERS - Attacked but earned less than {report['min_banners_threshold']} banners")
                print("=" * 140 + "\n")

                print(f"{'Player Name':<25} | {'Attacks':>7} | {'Wins':>5} | {'Off Banners':>11} | {'Def Banners':>11} | {'Total':>7} | {'Squads':>6} | {'Holds':>5}")
                print("-" * 140)

                for player in underperformers:
                    print(
                        f"{player['player_name']:<25} | "
                        f"{player['attacks']:>7} | "
                        f"{player['wins']:>5} | "
                        f"{player['offensive_banners']:>11} | "
                        f"{player['defensive_banners']:>11} | "
                        f"{player['total_banners']:>7} | "
                        f"{player['squads_deployed']:>6} | "
                        f"{player['defensive_holds']:>5}"
                    )
                print()
            else:
                print(f"✅ No underperformers - all attacking players earned at least {report['min_banners_threshold']} banners!\n")

            # Non-participants section
            non_participants = report.get('non_participants', [])
            if non_participants:
                print("=" * 140)
                print("NON-PARTICIPANTS - Did not attack or deploy defense")
                print("=" * 140 + "\n")

                for player in non_participants:
                    print(f"  - {player['player_name']}")
                print()
            else:
                print("✅ No non-participants - everyone participated!\n")

            # Full participation table
            print("=" * 140)
            print("FULL PARTICIPATION TABLE (sorted by banners)")
            print("=" * 140 + "\n")

            print(f"{'Player Name':<25} | {'Attacks':>7} | {'Wins':>5} | {'Off Banners':>11} | {'Def Banners':>11} | {'Total':>7} | {'Squads':>6} | {'Holds':>5}")
            print("-" * 140)

            for player in report.get('all_participants', []):
                print(
                    f"{player['player_name']:<25} | "
                    f"{player['attacks']:>7} | "
                    f"{player['wins']:>5} | "
                    f"{player['offensive_banners']:>11} | "
                    f"{player['defensive_banners']:>11} | "
                    f"{player['total_banners']:>7} | "
                    f"{player['squads_deployed']:>6} | "
                    f"{player['defensive_holds']:>5}"
                )

        except Exception as e:
            logger.error(f"Error running participation report: {e}")
            print(f"❌ Error: {e}")

        self._wait_for_enter()

    def run_all_reports(self):
        """Run all reports in sequence."""
        if not self._ensure_tw_data_loaded():
            return

        print("\n" + "=" * 80)
        print(" " * 20 + "RUNNING ALL REPORTS")
        print("=" * 80)

        self.run_tw_summary_report()
        print("\n" + "="*80 + "\n")
        self.run_leader_stats_report()
        print("\n" + "="*80 + "\n")
        self.run_defense_stats_report()
        print("\n" + "="*80 + "\n")
        self.run_participation_report()

    def run_ai_query(self):
        """Run a single AI query."""
        print("\n" + "=" * 80)
        print(" " * 20 + "AI QUERY MODE")
        print("=" * 80 + "\n")

        if not self._ensure_tw_data_loaded():
            return

        try:
            from swgoh_ai_analyzer import create_analyzer

            # Get query from user
            query = input("Enter your question: ").strip()
            if not query:
                print("No query entered.")
                self._wait_for_enter()
                return

            # Get AI provider preference
            provider = os.getenv('DEFAULT_AI_PROVIDER', 'openai')

            print(f"\n🤖 Analyzing with {provider}...")

            # Create analyzer
            analyzer = create_analyzer(
                data_file=str(self.tw_logs_file),
                provider=provider,
                guild_id=self.guild_id
            )

            # Run query
            response = analyzer.query(query)

            print("\n" + "=" * 80)
            print("AI RESPONSE:")
            print("=" * 80)
            print(response)
            print("=" * 80)

        except Exception as e:
            logger.error(f"Error running AI query: {e}")
            print(f"❌ Error: {e}")

        self._wait_for_enter()

    def run_ai_chat(self):
        """Run interactive AI chat mode."""
        print("\n" + "=" * 80)
        print(" " * 20 + "AI CHAT MODE")
        print("=" * 80 + "\n")

        if not self._ensure_tw_data_loaded():
            return

        try:
            from swgoh_ai_analyzer import create_analyzer

            provider = os.getenv('DEFAULT_AI_PROVIDER', 'openai')
            print(f"Provider: {provider}")
            print(f"Data file: {self.tw_logs_file}")
            print("\nType your questions about the TW data. Special commands:")
            print("  /clear    - Clear conversation history")
            print("  /history  - Show conversation history")
            print("  /export   - Export conversation to file")
            print("  /quit     - Exit chat mode")
            print("=" * 80 + "\n")

            # Create analyzer
            analyzer = create_analyzer(
                data_file=str(self.tw_logs_file),
                provider=provider,
                guild_id=self.guild_id
            )

            # Interactive loop
            while True:
                try:
                    user_input = input("You: ").strip()

                    if not user_input:
                        continue

                    # Handle special commands
                    if user_input.lower() == '/quit':
                        print("\nExiting chat mode.")
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
                    print("\n\nExiting chat mode.")
                    break
                except EOFError:
                    print("\n\nExiting chat mode.")
                    break
                except Exception as e:
                    logger.error(f"Error in chat: {e}")
                    print(f"\nError: {e}\n")

        except Exception as e:
            logger.error(f"Error starting AI chat: {e}")
            print(f"❌ Error: {e}")

        self._wait_for_enter()

    def show_settings_menu(self):
        """Display settings menu."""
        while True:
            self._clear_screen()
            print("=" * 80)
            print(" " * 25 + "SETTINGS")
            print("=" * 80)
            print()
            print(f"  Guild ID:    {self.guild_id}")
            print(f"  Ally Code:   {self.ally_code}")
            print(f"  Data Dir:    {self.data_dir}")
            print(f"  AI Provider: {os.getenv('DEFAULT_AI_PROVIDER', 'openai')}")
            print()
            print("-" * 80)
            print()
            print("  1. Change Guild ID")
            print("  2. Change Ally Code")
            print("  3. Change AI Provider")
            print("  4. Clear All Cached Data")
            print("  0. Back to Main Menu")
            print()
            print("=" * 80)

            choice = input("\nSelect option: ").strip()

            if choice == '0':
                break
            elif choice == '1':
                new_id = input(f"Enter new Guild ID (current: {self.guild_id}): ").strip()
                if new_id:
                    self.guild_id = new_id
                    print(f"✓ Guild ID updated to: {self.guild_id}")
                    self._wait_for_enter()
            elif choice == '2':
                new_code = input(f"Enter new Ally Code (current: {self.ally_code}): ").strip()
                if new_code:
                    self.ally_code = new_code
                    print(f"✓ Ally Code updated to: {self.ally_code}")
                    self._wait_for_enter()
            elif choice == '3':
                print("\nAvailable providers: openai, anthropic, google")
                new_provider = input("Enter provider: ").strip().lower()
                if new_provider in ['openai', 'anthropic', 'google']:
                    os.environ['DEFAULT_AI_PROVIDER'] = new_provider
                    print(f"✓ AI Provider set to: {new_provider}")
                else:
                    print("Invalid provider.")
                self._wait_for_enter()
            elif choice == '4':
                confirm = input("Are you sure you want to clear all cached data? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    try:
                        if self.tw_logs_file.exists():
                            self.tw_logs_file.unlink()
                        if self.guild_data_file.exists():
                            self.guild_data_file.unlink()
                        if self.metadata_file.exists():
                            self.metadata_file.unlink()
                        self.metadata = {'tw_logs_last_refresh': None, 'guild_roster_last_refresh': None}
                        print("✓ All cached data cleared.")
                    except Exception as e:
                        print(f"❌ Error clearing data: {e}")
                    self._wait_for_enter()
            else:
                print("Invalid option. Please try again.")
                self._wait_for_enter()

    def run(self):
        """Run the main menu loop."""
        while True:
            self.show_main_menu()
            choice = input("\nSelect option: ").strip()

            if choice == '0':
                print("\nGoodbye!")
                sys.exit(0)
            elif choice == '1':
                self.refresh_tw_logs()
                self._wait_for_enter()
            elif choice == '2':
                self.refresh_guild_roster()
                self._wait_for_enter()
            elif choice == '3':
                self.show_reports_menu()
            elif choice == '4':
                self.run_ai_query()
            elif choice == '5':
                self.run_ai_chat()
            elif choice == '6':
                self.show_settings_menu()
            else:
                print("Invalid option. Please try again.")
                self._wait_for_enter()


def main():
    """Main entry point for the menu system."""
    try:
        menu = SWGOHMenu()
        menu.run()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
