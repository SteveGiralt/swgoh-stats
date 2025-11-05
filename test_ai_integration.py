#!/usr/bin/env python3
"""
Test script for verifying AI integration

Tests basic functionality of the AI analyzer without making actual API calls.
"""

import sys
from pathlib import Path

# Test imports
print("Testing imports...")
try:
    from swgoh_data_context import SWGOHDataContext
    print("✓ swgoh_data_context imported successfully")
except ImportError as e:
    print(f"✗ Failed to import swgoh_data_context: {e}")
    sys.exit(1)

try:
    from swgoh_prompts import (
        get_single_query_prompt,
        get_chat_prompt,
        format_tw_summary,
        TW_DOMAIN_KNOWLEDGE
    )
    print("✓ swgoh_prompts imported successfully")
except ImportError as e:
    print(f"✗ Failed to import swgoh_prompts: {e}")
    sys.exit(1)

try:
    from swgoh_ai_analyzer import SWGOHAIAnalyzer, AIProvider, create_analyzer
    print("✓ swgoh_ai_analyzer imported successfully")
except ImportError as e:
    print(f"✗ Failed to import swgoh_ai_analyzer: {e}")
    sys.exit(1)

# Test prompt templates
print("\nTesting prompt templates...")
try:
    single_prompt = get_single_query_prompt()
    print(f"✓ Single query prompt created: {type(single_prompt).__name__}")

    chat_prompt = get_chat_prompt()
    print(f"✓ Chat prompt created: {type(chat_prompt).__name__}")
except Exception as e:
    print(f"✗ Failed to create prompt templates: {e}")
    sys.exit(1)

# Test data context (without loading actual data)
print("\nTesting data context...")
try:
    context = SWGOHDataContext()
    print(f"✓ Data context created with guild: {context.guild_name}")

    # Test with empty data
    summary = context.get_tw_summary()
    print(f"✓ TW summary generated (empty data): {summary}")

    # Test formatting
    formatted = format_tw_summary(summary)
    print(f"✓ Summary formatted: {len(formatted)} characters")
except Exception as e:
    print(f"✗ Failed to test data context: {e}")
    sys.exit(1)

# Test AI provider enum
print("\nTesting AI provider configuration...")
try:
    provider = AIProvider.ANTHROPIC
    print(f"✓ Anthropic provider: {provider.value}")

    provider = AIProvider.GOOGLE
    print(f"✓ Google provider: {provider.value}")
except Exception as e:
    print(f"✗ Failed to test AI providers: {e}")
    sys.exit(1)

print("\n" + "="*50)
print("All basic integration tests passed! ✓")
print("="*50)
print("\nNext steps:")
print("1. Install dependencies: pip install -r requirements.txt")
print("2. Set up API keys in .env file")
print("3. Test with actual TW logs data")
print("4. Integrate into swgoh_api_client.py CLI")
