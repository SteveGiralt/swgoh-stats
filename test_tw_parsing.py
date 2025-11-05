#!/usr/bin/env python3
"""
Quick test to verify TW logs parsing is working
"""

from swgoh_data_context import SWGOHDataContext

# Create context
context = SWGOHDataContext()

# Load TW logs
print("Loading TW logs...")
if context.load_tw_logs('twlogs.json'):
    print("✓ TW logs loaded successfully")

    # Get summary
    summary = context.get_tw_summary()

    print(f"\n{'='*60}")
    print("TW SUMMARY")
    print(f"{'='*60}")
    print(f"Guild: {summary.get('guild_name', 'N/A')}")
    print(f"Total Attacks: {summary.get('total_attacks', 0)}")
    print(f"Total Banners: {summary.get('total_banners', 0)}")
    print(f"Unique Players: {summary.get('unique_players', 0)}")
    print(f"Avg Banners/Attack: {summary.get('avg_banners', 0):.1f}")
    print(f"Avg Squad Power: {summary.get('avg_power', 0):,.0f}")

    if 'opponent_stats' in summary:
        opp = summary['opponent_stats']
        print(f"\nOpponent Guild:")
        print(f"Total Attacks: {opp.get('total_attacks', 0)}")
        print(f"Total Banners: {opp.get('total_banners', 0)}")
        print(f"Unique Players: {opp.get('unique_players', 0)}")
        print(f"Avg Banners/Attack: {opp.get('avg_banners', 0):.1f}")

    print(f"\n{'='*60}")
    print("TOP 5 PERFORMERS")
    print(f"{'='*60}")
    for i, player in enumerate(summary.get('top_performers', [])[:5], 1):
        print(f"{i}. {player['name']}: {player['total_banners']} banners ({player['attacks']} attacks, {player['avg_banners']:.1f} avg)")

    print(f"\n✓ Parsing successful!")
else:
    print("✗ Failed to load TW logs")
