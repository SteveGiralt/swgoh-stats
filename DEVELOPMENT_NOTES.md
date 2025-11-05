# SWGOH API Client - Development Notes

## API Endpoints Reference

### Authenticated Endpoints (breaks EA connection)
These endpoints require authentication and will break the user's game connection:

- `/activeraid` - Current raid data
- `/events` - Current and upcoming in-game events
- `/gac` - Grand Arena Championship (defense squads, match data, leaderboards)
- `/inventory` - Unequipped mods, currencies, materials, gear
- `/leaderboard` - Squad arena and fleet arena leaderboards
- `/squadfetch` - Saved squad and fleet loadouts
- `/tb` - Territory Battle data (platoons, leaderboards)
- `/tbleaderboardhistory` - Last 4 TBs leaderboard history
- `/tblogs` - Territory Battle logs (every action)
- `/tw` - Territory War data
- `/twleaderboard` - TW leaderboard (banners by attack/defend/total/rogue)
- `/twlogs` - TW logs (attacks, deployments, holds, preloads)

### Non-Authenticated Endpoints (does NOT break connection)
These endpoints are safe to use without breaking game connection:

- `/database` - SWGOH Registry interaction (special format - see details below)
- `/guild` - Guild data (members, raid results, TW results, profile)
- `/player` - Player data (roster, datacrons, stats, ratings)

**IMPORTANT:** Use non-authenticated endpoints when possible to avoid disrupting gameplay!

### Database Endpoint Details

The `/database` endpoint is used to retrieve registration data linking SWGOH allycodes to Discord IDs.

**SPECIAL FORMAT - DIFFERENT FROM OTHER ENDPOINTS!**

**Full URL:** `https://mhanndalorianbot.work/api/database` (NOT `/api` like other endpoints)

**Headers (DIFFERENT from other endpoints):**
```
api-key: your_api_key_here
Content-Type: application/json
```
- Uses `api-key` header (NOT `Api-Key` or other variant)
- Does NOT use `discordId` header
- Does NOT use `allyCode` header

**Request Body Format:**
```json
{
  "user": ["859194332", "123456789012345678"],
  "endpoint": "find"
}
```

**Key Points:**
- The `user` field accepts an array of strings (max 50 items)
- Each string can be either an allycode or a Discord ID
- The `endpoint` field must be set to `"find"`
- Unlike other endpoints, all parameters go in the request body

**Response Format:**
```json
{
  "allyCode": "string",
  "discordId": "string",
  "verified": boolean,
  "primary": boolean  // conditionally included
}
```

**Response Fields:**
- `allyCode` - Always included
- `discordId` - Always included
- `verified` - Always included (whether registration is verified)
- `primary` - Conditionally included (whether this is primary account)

**Comparison to Other Endpoints:**
```
Regular endpoints:
  URL: https://mhanndalorianbot.work/api
  Headers: Api-Key, discordId
  Body: { "payload": { ... } }

Database endpoint:
  URL: https://mhanndalorianbot.work/api/database
  Headers: api-key, Content-Type
  Body: { "user": [...], "endpoint": "find" }
```

## Territory Wars Game Mechanics

### Territory Map Layout

**Zone Naming Convention:**
```
         T1    T2    T3    T4        (Top Row - Back Territories)
              M1         M2          (Middle Row - Middle Territories)
    B1    B2    B3    B4             (Bottom Row - Front Territories)
```

**Zone Tier Values:**
- **Back Row (T zones)**: 900 base banners when fully cleared (doubled value)
- **Middle Row (M zones)**: 450 base banners when fully cleared
- **Front Row (B zones)**: 450 base banners when fully cleared
- **PLUS**: +10 banners per defensive squad/fleet slot in that territory

**Territory Defense Slots:**
- Number of defensive squads/fleets per territory varies by TW
- Depends on total guild participation and matchmaking factors
- Each territory can have a different number of defensive slots
- Total conquest value = base banners + (10 × number of defense slots in that territory)

**Attack Progression:**
- Must clear front territories (B1-B4) before accessing middle (M1-M2)
- Must clear middle territories before accessing back (T1-T4)
- Cannot skip ahead to higher value territories

### Attack Phase Banner Scoring

**Offense Victory Bonuses:**
- Base Attack Success: +5 Banners
- First Attempt Victory: +10 Banners (total: 15)
- Second Attempt Victory: +5 Banners (total: 10)
- Survivor Bonus: +1 Banner per surviving unit (max +5)
- Slot Bonus: +1 Banner per empty slot if using <5 units (max +4)
- **Maximum possible**: 64 Banners per attack

**Banner Efficiency Tiers:**
- **High Efficiency**: 60+ banners (clean first attempt win with survivors)
- **Medium Efficiency**: 40-59 banners (first attempt with losses, or second attempt)
- **Low Efficiency**: <40 banners (multiple attempts or heavy losses)

**Strategic Context:**
- Each unit can only be used once (defense OR offense)
- Failed attacks still lock characters from future use
- Defensive squads have persistent health/turn meter
- Poor coordination (feeding turn meter) hurts the entire guild
- Territories must be cleared front-to-back

**Territory Conquest Bonuses (not in attack logs):**
- +450 Banners per front/middle territory cleared
- +900 Banners per back territory cleared (doubled)
- +10 Banners per defensive squad slot

**Defense Bonuses (not in attack logs):**
- Set Squad: +30 Banners
- Set Fleet: +34 Banners

## Critical Data Structure Information

### TW Logs Event Structure - SQUAD_WIN Events

**VERY IMPORTANT:** The field naming in SQUAD_WIN events is counterintuitive:

```
In a SQUAD_WIN event:
- info.authorId / info.authorName = THE ATTACKER (who won the battle)
- warSquad.playerId / warSquad.playerName = THE DEFENDER (who lost/was defeated)

DO NOT CONFUSE THESE - they are backwards from what you might expect!
```

### Guild ID in Zone Data

```
zoneData.guildId = THE ATTACKING GUILD'S ID

So if zoneData.guildId == our_guild_id:
  → WE are attacking (our guild's attack)

If zoneData.guildId != our_guild_id:
  → OPPONENT is attacking (opponent guild's attack)
```

### Event Types
- `TERRITORY_CHANNEL_ACTIVITY_CONFLICT_SQUAD_WIN` = Successful attack (earns banners)
- `TERRITORY_CHANNEL_ACTIVITY_CONFLICT_DEFENSE_DEPLOY` = Defense placement
- `TERRITORY_CHANNEL_ACTIVITY_CONFLICT_DEFENSE_FLEET_DEPLOY` = Fleet defense placement
- `EMPTY` with `squadStatus == 2` = Attack attempt (may include losses)

### Tracking Defeats/Losses

To count how many times a player lost on attack:
1. Look at SQUAD_WIN events where they appear as the DEFENDER
2. Count when `warSquad.playerName == player_name` (they were defeated)

This gives you total attacks = wins + defeats

## Guild Information

- **Our Guild ID**: `BQ4f8IJyRma4IWSSCurp4Q`
- **Our Guild Name**: `DarthJedii56`
- Default ally code: `657146191`

## API Response Compression

The API returns compressed responses. Handle this by:
- Using `Accept-Encoding: gzip,deflate` (NOT `br` - brotli causes issues)
- Let Python `requests` library handle decompression automatically
- DO NOT manually specify `br` (brotli) encoding

## Common Pitfalls

1. **Attacker/Defender confusion**: Always remember `info.authorName` is attacker in SQUAD_WIN
2. **Guild ID confusion**: `zoneData.guildId` is the ATTACKING guild, not defending
3. **Output file format**: TW logs saved via `--output` include header text before JSON
4. **Failed attacks**: Only successful attacks (SQUAD_WIN) are in the logs; losses must be inferred

## Code Patterns

### Parsing TW Logs
```python
# Correct pattern:
attacker_name = info.get('authorName')  # Who won
defender_name = warSquad.get('playerName')  # Who lost
guild_id = zoneData.get('guildId')  # Attacking guild

# Check if attack is by our guild:
if guild_id == our_guild_id:
    our_attacks.append(attack_data)
else:
    opponent_attacks.append(attack_data)
```

### Counting Defeats
```python
# Count defeats for our guild:
# When our players appear as DEFENDERS in opponent attacks
our_defeats = opponent_df.groupby(['defender_id', 'defender_name']).size()
```

## Testing Verification Points

When testing TW analysis:
- **tomasmm** should show 2/3 (2 wins, 3 total attacks)
- **Exar Kun** is in our guild (DarthJedii56)
- **AAckbar** is in the opponent guild

## Display Formats

### Attacks Column
- Show "X/Y" when player has losses (X wins out of Y total)
- Show just "X" when player has no losses
- Example: "2/3" means 2 wins, 3 total (1 loss)

## Configuration Management

### Environment Variables (.env file)
The project now uses `python-dotenv` to load credentials from a `.env` file automatically.

**Setup:**
```bash
cp .env.example .env
# Edit .env with your credentials
```

**.env file contents:**
```bash
SWGOH_API_KEY=your_api_key_here
SWGOH_DISCORD_ID=your_discord_id_here
```

**Priority:** Command-line args > .env file > Environment variables

### Guild Name Extraction
The guild name is automatically fetched from the API during TW analysis:
- If credentials available: Fetches from `/api/guild` endpoint (`events.guild.name`)
- If no credentials: Falls back to "DarthJedii56"
- No need to pass `--guild-name` anymore!

## Future Improvements Needed

1. Extract opponent guild name from data
2. Add support for tracking defense deployments
3. Add zone-by-zone analysis
4. Track successful defenses
5. Add timeline analysis of attacks
6. Implement other endpoints (/gac, /tb, /player analysis, etc.)
