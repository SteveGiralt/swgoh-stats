# SWGOH Data Analyzer - Menu System Guide

## Overview

The SWGOH Data Analyzer now features an interactive menu-driven interface that makes it easy to:
- Refresh data from the API
- View data refresh timestamps
- Run various TW (Territory Wars) reports
- Query data using AI
- Manage settings

## Quick Start

### Launch the Menu

Simply run the program without any arguments:

```bash
python swgoh_api_client.py
```

Or use the convenient launcher:

```bash
./swgoh
```

Or explicitly request the menu:

```bash
python swgoh_api_client.py --menu
```

### Legacy CLI Mode

The old CLI interface is still available for scripting and automation:

```bash
# Fetch TW logs
python swgoh_api_client.py --endpoint twlogs --ally-code 657146191 --output tw_logs.json

# Run analysis
python swgoh_api_client.py --endpoint analyze-tw --input-file tw_logs.json
```

## Menu System Features

### Main Menu

```
================================================================================
                    SWGOH DATA ANALYZER
================================================================================

📊 DATA STATUS:
   TW Logs:      Last refreshed: 2025-11-05 02:30 PM
   Guild Roster: Last refreshed: 2025-11-05 02:25 PM

--------------------------------------------------------------------------------

MENU OPTIONS:

  1. Refresh TW Logs
  2. Refresh Guild Roster
  3. Run Reports
  4. AI Query (Interactive)
  5. AI Chat (Conversation Mode)
  6. Settings
  0. Exit

================================================================================
```

### Option 1: Refresh TW Logs

Fetches the latest Territory Wars logs from the API and caches them locally.

- Uses the ally code from your settings or `.env` file
- Saves data to `~/.swgoh_data/tw_logs.json`
- Updates the "last refreshed" timestamp
- This data is required for all reports

### Option 2: Refresh Guild Roster

Fetches the current guild roster from the API.

- Uses the guild ID from your settings or `.env` file
- Saves data to `~/.swgoh_data/guild_data.json`
- Updates the "last refreshed" timestamp
- Used for participation reports to identify non-participants

### Option 3: Run Reports

Opens a submenu with various report options:

#### Reports Submenu

```
================================================================================
                         REPORTS MENU
================================================================================

  1. TW Attack Summary
  2. Leader Stats (Defending Leaders)
  3. Defense Stats (Defense Contributors)
  4. Participation Report
  5. All Reports (Full Analysis)
  0. Back to Main Menu
```

**Report Types:**

1. **TW Attack Summary** - Shows offensive performance for both guilds
   - Total attacks, banners, and efficiency
   - Per-player attack statistics
   - Win/loss tracking

2. **Leader Stats** - Analyzes defending squad leaders
   - Enemy leaders you attacked (sorted by hold rate)
   - Your defending leaders opponent attacked
   - Win rate, hold rate, and banner averages
   - Optional detailed per-player breakdown

3. **Defense Stats** - Shows defensive contributions
   - Who deployed defenses
   - Squad counts and power levels
   - How defenses performed (hold rates)
   - Banners given up

4. **Participation Report** - Identifies participation issues
   - Lists all participants
   - Flags underperformers (low banner earners)
   - Identifies non-participants
   - Shows offensive + defensive contributions

5. **All Reports** - Runs all reports in sequence

### Option 4: AI Query (Interactive)

Run a single natural language query against your TW data.

Example queries:
- "Who was our top performer?"
- "How many attacks did we make?"
- "What was our average banner efficiency?"
- "Which leaders gave us the most trouble?"

The AI will analyze your data and provide a concise answer.

### Option 5: AI Chat (Conversation Mode)

Enter an interactive chat session with the AI analyzer.

**Features:**
- Ask multiple questions in conversation
- AI remembers context from previous questions
- Special commands:
  - `/clear` - Clear conversation history
  - `/history` - Show conversation history
  - `/export [filename]` - Export conversation to file
  - `/quit` - Exit chat mode

**Example Session:**
```
You: How many attacks did we make?
AI: 99 attacks.

You: Who had the best efficiency?
AI: Exar Kun with 19.8 average banners per attack (9 attacks, 178 total banners).

You: What about the opponent?
AI: The opponent made 103 attacks with 18.5 average banners per attack.
```

### Option 6: Settings

Configure the analyzer:

```
================================================================================
                           SETTINGS
================================================================================

  Guild ID:    BQ4f8IJyRma4IWSSCurp4Q
  Ally Code:   657146191
  Data Dir:    /Users/you/.swgoh_data
  AI Provider: openai

--------------------------------------------------------------------------------

  1. Change Guild ID
  2. Change Ally Code
  3. Change AI Provider
  4. Clear All Cached Data
  0. Back to Main Menu
```

**Settings Options:**

1. **Change Guild ID** - Set a different guild to analyze
2. **Change Ally Code** - Set a different ally code for TW logs
3. **Change AI Provider** - Switch between OpenAI, Anthropic, or Google
4. **Clear All Cached Data** - Delete all cached data files and timestamps

## Data Storage

All data is cached locally in `~/.swgoh_data/`:

- `tw_logs.json` - Territory Wars logs
- `guild_data.json` - Guild roster
- `metadata.json` - Timestamps and settings

This allows you to:
- Run reports without re-fetching data
- Work offline once data is cached
- Track when data was last refreshed
- Avoid unnecessary API calls

## Environment Variables

Configure these in your `.env` file:

```bash
# Required for API access
SWGOH_API_KEY=your_api_key_here
SWGOH_DISCORD_ID=your_discord_id_here

# Optional (has defaults)
SWGOH_GUILD_ID=BQ4f8IJyRma4IWSSCurp4Q
SWGOH_ALLY_CODE=657146191
DEFAULT_AI_PROVIDER=openai
```

## Workflow Example

Typical workflow for analyzing a Territory War:

1. **Launch the menu**
   ```bash
   ./swgoh
   ```

2. **Refresh data** (options 1 & 2)
   - Refresh TW Logs to get latest battle data
   - Refresh Guild Roster to identify participants

3. **Run reports** (option 3)
   - Start with "All Reports" for comprehensive overview
   - Or run specific reports as needed

4. **Use AI for insights** (options 4 or 5)
   - Ask specific questions about the data
   - Get strategic recommendations
   - Compare players or identify patterns

5. **Export results**
   - In AI Chat mode, use `/export` to save analysis

## Tips

- **Refresh data before each war** to ensure accuracy
- **Use AI Chat mode** for exploratory analysis
- **Use AI Query mode** for quick single questions
- **Check timestamps** on main menu to know data freshness
- **Clear cache** (Settings → Option 4) if data seems stale

## Troubleshooting

**"No TW logs found"**
- Run Option 1 to refresh TW logs first

**"API credentials not found"**
- Check your `.env` file has `SWGOH_API_KEY` and `SWGOH_DISCORD_ID`

**AI features not working**
- Ensure you have the required API keys for your AI provider
- Check `DEFAULT_AI_PROVIDER` environment variable

**Reports showing old data**
- Check the "Last refreshed" timestamps on main menu
- Refresh data using options 1 and 2

## Advanced Usage

### Scripting with CLI Mode

While the menu is great for interactive use, you can still use CLI mode for automation:

```bash
# Daily data refresh script
python swgoh_api_client.py --endpoint twlogs --output tw_logs.json
python swgoh_api_client.py --endpoint guild --guild-id YOUR_GUILD_ID --output guild.json

# Generate reports
python swgoh_api_client.py --endpoint analyze-tw --input-file tw_logs.json --output report.txt
python swgoh_api_client.py --endpoint participation --input-file tw_logs.json --output participation.txt
```

### Custom AI Models

Specify a custom AI model via environment variable:

```bash
# For OpenAI
export OPENAI_MODEL=gpt-4o

# For Anthropic
export ANTHROPIC_MODEL=opus
```

## What's Next?

The menu system provides a user-friendly interface to all the analyzer's features. All the original CLI functionality remains available for scripting and automation.

Enjoy analyzing your Territory Wars!
