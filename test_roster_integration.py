#!/usr/bin/env python3
"""
Test roster integration with participation report
"""

from swgoh_data_context import SWGOHDataContext

# Create context
context = SWGOHDataContext()

# Load TW logs
print("Loading TW logs...")
if not context.load_tw_logs('twlogs.json'):
    print("✗ Failed to load TW logs")
    exit(1)

print("✓ TW logs loaded")

# Load guild data
print("\nLoading guild roster...")
if not context.load_guild_data('guild_data.json'):
    print("✗ Failed to load guild data")
    exit(1)

print("✓ Guild data loaded")

# Get roster
roster = context.get_guild_roster()
print(f"✓ Extracted {len(roster)} players from guild roster")

# Get participation report
print("\nGenerating participation report...")
report = context.get_participation_report(min_banners=50, min_attacks=1)

print(f"\n{'='*60}")
print("PARTICIPATION SUMMARY")
print(f"{'='*60}")
print(f"Total Players: {report['total_players']}")
print(f"Players Who Attacked: {report['players_who_attacked']}")
print(f"Players Who Deployed: {report['players_who_defended']}")
print(f"Underperformers: {len(report['underperformers'])}")
print(f"Complete Non-Participants: {len(report['non_participants'])}")

if report['non_participants']:
    print(f"\n{'='*60}")
    print("COMPLETE NON-PARTICIPANTS")
    print(f"{'='*60}")
    for player in report['non_participants']:
        print(f"  - {player['player_name']}")

print(f"\n✓ Test completed successfully!")
