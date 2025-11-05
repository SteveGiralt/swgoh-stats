#!/usr/bin/env python3
"""
SWGOH Domain-Specific Prompts for AI Analysis

This module contains prompt templates and domain knowledge for analyzing
Star Wars Galaxy of Heroes data, particularly Territory Wars logs.
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Territory Wars Domain Knowledge
TW_DOMAIN_KNOWLEDGE = """
## Territory Wars Domain Knowledge

### Territory Map Layout
```
         T1    T2    T3    T4        (Top Row - Back Territories)
              M1         M2          (Middle Row - Middle Territories)
    B1    B2    B3    B4             (Bottom Row - Front Territories)
```

**Zone Values:**
- **Back Row (T1-T4)**: 900 base banners per territory (doubled value) - highest priority
- **Middle Row (M1-M2)**: 450 base banners per territory
- **Front Row (B1-B4)**: 450 base banners per territory - must clear first
- **PLUS**: +10 banners per defensive squad/fleet slot in that territory

**Attack Progression:**
- Must clear front row (B zones) → middle row (M zones) → back row (T zones)
- Cannot skip tiers
- Back territories worth 2x base value

### Banner Scoring System

**Offense Victory Bonuses:**
- Base Attack Success: +5 Banners
- First Attempt Victory: +10 Banners (total: 15)
- Second Attempt Victory: +5 Banners (total: 10)
- Survivor Bonus: +1 Banner per surviving unit (max +5)
- Slot Bonus: +1 Banner per empty slot if using <5 units (max +4)
- **Maximum possible**: 64 Banners per attack

**Banner Efficiency Tiers:**
- **High Efficiency**: 60+ banners = Clean first attempt win with survivors
- **Medium Efficiency**: 40-59 banners = First attempt with losses, or second attempt
- **Low Efficiency**: <40 banners = Multiple attempts or heavy losses
- **Banner per Power Ratio**: banners / (squad_power/1000) = efficiency metric

**Strategic Context:**
- Players can only use each unit once (on defense OR offense)
- Failed attacks still "lock" those characters from being used again
- Defensive squads have persistent health/turn meter across attacks
- Coordination matters: feeding turn meter hurts the guild
- Territories must be cleared front-to-back

### Territory Conquest Bonuses (not in attack logs):
- +450 Banners per front/middle territory cleared
- +900 Banners per back territory cleared (doubled)
- +10 Banners per defensive squad slot

### Defense Bonuses (not in attack logs):
- Set Squad: +30 Banners
- Set Fleet: +34 Banners
"""

# Critical Data Structure Warnings
DATA_STRUCTURE_WARNINGS = """
## CRITICAL Data Structure Information

**VERY IMPORTANT - Field Naming:**
In SQUAD_WIN events (attack logs), the field naming is counterintuitive:
- `authorId` / `authorName` = THE ATTACKER (who won the battle)
- `warSquad.playerId` / `warSquad.playerName` = THE DEFENDER (who lost/was defeated)

**Guild ID Context:**
- `zoneData.guildId` = THE ATTACKING GUILD'S ID
- If `zoneData.guildId` matches our guild ID → WE are attacking
- If `zoneData.guildId` does NOT match → OPPONENT is attacking

**Event Types:**
- `TERRITORY_CHANNEL_ACTIVITY_CONFLICT_SQUAD_WIN` = Successful attack (earns banners)
- `TERRITORY_CHANNEL_ACTIVITY_CONFLICT_DEFENSE_DEPLOY` = Defense placement
- `EMPTY` with `squadStatus == 2` = Attack attempt (may include losses)
"""

# System prompt for TW analysis
TW_ANALYSIS_SYSTEM_PROMPT = f"""You are a Territory Wars data analyst for Star Wars Galaxy of Heroes.

{TW_DOMAIN_KNOWLEDGE}

{DATA_STRUCTURE_WARNINGS}

## Response Guidelines

**Be Direct and Concise:**
- Answer the specific question asked - nothing more, nothing less
- Use exact numbers from the data
- Keep responses short unless the user asks for detail
- Only provide context or strategy when explicitly requested
- Use bullet points or simple formatting, not elaborate sections

**Examples:**

Question: "How many attacks did we make?"
Good: "99 attacks."
Bad: "Based on the Territory Wars data summary... [3 paragraphs]"

Question: "Who was our top performer?"
Good: "Exar Kun with 178 banners (9 attacks, 19.8 avg)."
Bad: "### Top Performer Analysis... [extensive breakdown]"

Question: "Analyze our performance"
Good: [Now provide detailed analysis since requested]
Bad: [Still keep it focused and structured]

**Only add strategic insights, comparisons, or context when:**
- The user asks "why", "how", or "analyze"
- The user requests recommendations or strategy
- The numbers require explanation to be meaningful

Be helpful, accurate, and concise. Don't over-explain simple questions."""


# Prompt template for single query mode
def get_single_query_prompt() -> ChatPromptTemplate:
    """
    Get the prompt template for single-query analysis mode.

    Returns:
        ChatPromptTemplate configured for one-shot TW analysis
    """
    return ChatPromptTemplate.from_messages([
        ("system", TW_ANALYSIS_SYSTEM_PROMPT),
        ("human", """Here is the Territory Wars data summary:

{context}

User Question: {query}

Please provide a clear, accurate analysis based on the data above.""")
    ])


# Prompt template for interactive chat mode
def get_chat_prompt() -> ChatPromptTemplate:
    """
    Get the prompt template for interactive chat mode with conversation history.

    Returns:
        ChatPromptTemplate configured for multi-turn conversations
    """
    return ChatPromptTemplate.from_messages([
        ("system", TW_ANALYSIS_SYSTEM_PROMPT),
        ("system", """The following is a summary of the Territory Wars data you're analyzing:

{context}

This data remains available throughout our conversation. Reference it as needed to answer questions."""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{query}")
    ])


# Helper function to build context summaries
def format_tw_summary(summary_stats: dict) -> str:
    """
    Format TW summary statistics into a readable context string for the LLM.

    Args:
        summary_stats: Dictionary containing TW summary data

    Returns:
        Formatted string with TW data summary
    """
    context_parts = []

    # Guild overview
    if 'guild_name' in summary_stats:
        context_parts.append(f"## Guild: {summary_stats['guild_name']}")
        context_parts.append("")

    # Overall statistics
    if 'total_attacks' in summary_stats:
        context_parts.append("### Overall Statistics")
        context_parts.append(f"- Total Attacks: {summary_stats.get('total_attacks', 'N/A')}")
        context_parts.append(f"- Total Banners: {summary_stats.get('total_banners', 'N/A')}")
        context_parts.append(f"- Unique Players: {summary_stats.get('unique_players', 'N/A')}")
        context_parts.append(f"- Average Banners/Attack: {summary_stats.get('avg_banners', 'N/A'):.1f}")
        context_parts.append("")

    # Top performers table
    if 'top_performers' in summary_stats:
        context_parts.append("### Top 10 Performers")
        context_parts.append("")
        context_parts.append("| Player | Attacks | Banners | Avg Banners | Avg Power |")
        context_parts.append("|--------|---------|---------|-------------|-----------|")

        for player in summary_stats['top_performers'][:10]:
            context_parts.append(
                f"| {player['name']} | {player['attacks']} | "
                f"{player['total_banners']} | {player['avg_banners']:.1f} | "
                f"{player['avg_power']:,.0f} |"
            )
        context_parts.append("")

    # Guild comparison
    if 'opponent_stats' in summary_stats:
        context_parts.append("### Guild Comparison")
        context_parts.append("")
        context_parts.append("| Metric | Our Guild | Opponent |")
        context_parts.append("|--------|-----------|----------|")

        our_stats = summary_stats
        opp_stats = summary_stats['opponent_stats']

        context_parts.append(f"| Total Attacks | {our_stats.get('total_attacks', 0)} | {opp_stats.get('total_attacks', 0)} |")
        context_parts.append(f"| Total Banners | {our_stats.get('total_banners', 0)} | {opp_stats.get('total_banners', 0)} |")
        context_parts.append(f"| Avg Banners/Attack | {our_stats.get('avg_banners', 0):.1f} | {opp_stats.get('avg_banners', 0):.1f} |")
        context_parts.append(f"| Unique Players | {our_stats.get('unique_players', 0)} | {opp_stats.get('unique_players', 0)} |")
        context_parts.append("")

    # Additional context note
    context_parts.append("*Note: Full detailed data is available if you need specific player lookups or deeper analysis.*")

    return "\n".join(context_parts)


# Example queries for testing
EXAMPLE_QUERIES = [
    "How many total attacks did we make?",
    "Who had the best banner efficiency?",
    "Compare our top 5 attackers to the opponent's top 5",
    "What's our average banner per attack compared to the opponent?",
    "Who attacked the most?",
    "Analyze our attack patterns and identify any weaknesses",
    "Which players had the highest banner efficiency?",
    "Show me statistics for player [name]",
    "How does our guild participation compare to the opponent?",
]
