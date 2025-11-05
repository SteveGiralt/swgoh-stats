# SWGOH API Client

A Python client for interacting with the Mhanndalorian Bot API to retrieve Star Wars Galaxy of Heroes data.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

### Option 1: Using .env file (Recommended)

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```bash
   SWGOH_API_KEY=your_api_key_here
   SWGOH_DISCORD_ID=your_discord_id_here
   ```

The `.env` file is automatically loaded when you run the client and is ignored by git to keep your credentials safe.

### Option 2: Using environment variables

```bash
export SWGOH_API_KEY="your_api_key_here"
export SWGOH_DISCORD_ID="your_discord_id_here"
```

### Option 3: Using command-line arguments

Pass credentials directly when running commands:
```bash
python swgoh_api_client.py --api-key "your_key" --discord-id "your_id" --endpoint twlogs
```

## Usage

### Get Territory War Logs

```bash
# Using environment variables
python swgoh_api_client.py --ally-code 859194332

# With explicit credentials
python swgoh_api_client.py \
  --api-key "your_api_key" \
  --discord-id "your_discord_id" \
  --ally-code 859194332

# Save output to file
python swgoh_api_client.py --ally-code 859194332 --output twlogs.json

# Use HMAC authentication (required for multi-user access)
python swgoh_api_client.py --ally-code 859194332 --use-hmac
```

### Get Player Data

```bash
python swgoh_api_client.py --ally-code 859194332 --endpoint player
```

### Get Guild Data

```bash
# Get full guild data (uses default guild ID: BQ4f8IJyRma4IWSSCurp4Q)
python swgoh_api_client.py --endpoint guild

# Get just the player list from the default guild
python swgoh_api_client.py --endpoint guild-players

# Get just the player list (alternative method)
python swgoh_api_client.py --endpoint guild --list-players

# Use a different guild ID
python swgoh_api_client.py --endpoint guild --guild-id "other_guild_id"

# Save guild player list to file
python swgoh_api_client.py --endpoint guild-players --output guild_players.json
```

### Look Up Registration Data

```bash
# Look up registration data by allycode
python swgoh_api_client.py --endpoint database --ally-code 859194332

# Look up by Discord ID
python swgoh_api_client.py --endpoint database --discord-id "123456789012345678"

# Look up multiple users at once (up to 50)
python swgoh_api_client.py --endpoint database --user-ids "859194332,987654321,123456789012345678"

# Save results to file
python swgoh_api_client.py --endpoint database --ally-code 859194332 --output registry.json
```

The response includes:
- `allyCode`: The player's allycode
- `discordId`: The linked Discord ID
- `verified`: Whether the registration is verified
- `primary`: Whether this is the primary account (when available)

### Analyze Territory War Logs

```bash
# Analyze TW logs from a file (no API credentials needed)
python swgoh_api_client.py --endpoint analyze-tw --input-file twlogs.json

# Save analysis results to a file
python swgoh_api_client.py --endpoint analyze-tw --input-file twlogs.json --output tw_summary.txt

# Output as JSON for further processing
python swgoh_api_client.py --endpoint analyze-tw --input-file twlogs.json --json --output tw_summary.json
```

The analysis will show:
- Total number of successful attacks
- Number of unique players who attacked
- Per-player statistics:
  - Number of attacks
  - Total banners earned
  - Average banners per attack
  - Average squad power used

### Additional Options

- `--enums`: Return enum values in response
- `--verbose` or `-v`: Enable verbose logging
- `--json`: Output as formatted JSON
- `--output FILE` or `-o FILE`: Write output to file

## API Endpoints

The client supports the following endpoints:

- `twlogs` (default): Territory War attack/deployment/hold records
- `player`: Player profile, roster, and datacrons
- `guild`: Guild profile, members, and raid results
- `guild-players`: Extract just the player list from a guild (sorted by galactic power)
- `database`: Look up registration data linking allycodes to Discord IDs
- `analyze-tw`: Analyze TW logs from a file (local analysis, no API credentials needed)

## Examples

```bash
# Get TW logs with verbose output
python swgoh_api_client.py --ally-code 859194332 -v

# Get player data with enums
python swgoh_api_client.py --ally-code 859194332 --endpoint player --enums

# Get TW logs and save to file
python swgoh_api_client.py --ally-code 859194332 --output my_tw_logs.json
```

## Notes

- The API requires a Patreon subscription ($1/month) and setup through the Mhanndalorian Discord bot
- Simple API key authentication is suitable for single-user access
- HMAC authentication is required for multi-user applications
- All requests are POST requests to `https://mhanndalorianbot.work/api`
