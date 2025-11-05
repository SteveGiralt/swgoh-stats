# AI Q&A Analysis Project

## Project Overview

Adding AI-powered natural language query capabilities to the SWGOH API Client using LangChain for flexible LLM integration.

### Goals
- Enable natural language queries against SWGOH data (TW logs, player rosters, guild info)
- Support multiple LLM providers (Claude, Gemini, future models)
- Provide both single-query and interactive chat modes
- Maintain conversation context for multi-turn analysis
- Build extensible architecture for future enhancements

---

## Architecture

```
User Query → CLI → LangChain Chain → LLM (Claude/Gemini) → Parser → Output
                         ↓
                   Prompt Template
                         ↓
                   Context Builder
                         ↓
                   Data Loaders
              (TW/Player/Guild JSON)
```

### Key Components
1. **Data Context Builder**: Loads and summarizes SWGOH data for LLM context
2. **Prompt Templates**: Domain-specific prompts with SWGOH knowledge
3. **AIAnalyzer Class**: Main interface using LangChain abstractions
4. **CLI Integration**: New endpoints `ai-query` and `ai-chat`
5. **Model Factory**: Abstraction layer for swapping LLM providers

---

## Implementation Phases

### Phase 1: Foundation ✅ COMPLETED
**Status**: Completed
**Target**: Session 1-2

- [x] Design architecture with LangChain
- [x] Document project plan
- [x] Update requirements.txt with dependencies
- [x] Set up basic LangChain structure
- [x] Create model factory pattern

**Dependencies Added**:
```
langchain>=0.1.0
langchain-anthropic>=0.1.0
langchain-google-genai>=0.1.0
langchain-community>=0.1.0
langchain-core>=0.1.0
```

**Files Created**:
- `swgoh_prompts.py` - TW-specific prompts and domain knowledge
- `swgoh_data_context.py` - Data loading and summarization
- `swgoh_ai_analyzer.py` - LangChain AI analyzer with model factory
- `test_ai_integration.py` - Basic integration tests

---

### Phase 2: Core Components
**Status**: Not Started
**Target**: Session 2-3

#### 2.1: Data Context System
- [ ] Create `SWGOHDataContext` class
- [ ] Implement TW log data loader and summarizer
- [ ] Implement guild data loader
- [ ] Implement player data loader
- [ ] Build smart summarization (token-aware)
- [ ] Add data validation

**Files to Create**:
- `swgoh_data_context.py`

#### 2.2: Prompt Engineering
- [ ] Create system prompt for TW analysis
- [ ] Add SWGOH domain knowledge to prompts
- [ ] Include critical data structure warnings
- [ ] Build prompt templates with LangChain
- [ ] Test prompt effectiveness with sample queries

**Files to Create**:
- `swgoh_prompts.py`

---

### Phase 3: AI Analyzer Implementation
**Status**: Not Started
**Target**: Session 3-4

- [ ] Create `AIAnalyzer` class
- [ ] Implement model factory (Claude/Gemini support)
- [ ] Add conversation memory management
- [ ] Build single query mode
- [ ] Implement response formatting
- [ ] Add error handling and fallbacks
- [ ] Test with various query types

**Files to Create**:
- `swgoh_ai_analyzer.py`

---

### Phase 4: CLI Integration ✅ COMPLETED
**Status**: Completed
**Target**: Session 3

- [x] Add `ai-query` endpoint to CLI
- [x] Add `ai-chat` endpoint to CLI
- [x] Add provider selection flags (`--ai-provider`)
- [x] Add model selection flags (`--ai-model`)
- [x] Add API key configuration
- [x] Update environment variable handling
- [x] Add output formatting options

**Files Modified**:
- `swgoh_api_client.py` (main CLI)

---

### Phase 5: Interactive Chat Mode
**Status**: Not Started
**Target**: Session 5-6

- [ ] Implement interactive REPL
- [ ] Add conversation history display
- [ ] Add context management commands
- [ ] Add special commands (/clear, /history, /export)
- [ ] Add session saving/loading
- [ ] Improve UX with colored output

---

### Phase 6: Testing & Refinement
**Status**: Not Started
**Target**: Session 6-7

- [ ] Create test data sets
- [ ] Test common query patterns
- [ ] Refine prompts based on results
- [ ] Test with both Claude and Gemini
- [ ] Benchmark costs and performance
- [ ] Add unit tests
- [ ] Create integration tests

**Files to Create**:
- `tests/test_ai_analyzer.py`
- `tests/test_data_context.py`
- `tests/fixtures/sample_queries.json`

---

### Phase 7: Documentation & Examples
**Status**: Not Started
**Target**: Session 7

- [ ] Update README.md with AI features
- [ ] Add usage examples
- [ ] Document prompt templates
- [ ] Create query cookbook
- [ ] Add troubleshooting guide
- [ ] Document API key setup

---

### Phase 8: Advanced Features (Future)
**Status**: Not Started
**Target**: Future sessions

- [ ] RAG implementation for large datasets
- [ ] Multi-document analysis
- [ ] Data visualization generation
- [ ] Export analysis reports
- [ ] Custom prompt templates (user-defined)
- [ ] Cost tracking and budgets
- [ ] Structured output parsing (JSON/tables)
- [ ] Agent-based complex workflows
- [ ] Caching layer for common queries

---

## Technical Specifications

### SWGOH Territory Wars Domain Knowledge

#### Territory Map Layout

**Zone Naming Convention:**
```
         T1    T2    T3    T4        (Top Row - Back Territories)
              M1         M2          (Middle Row - Middle Territories)
    B1    B2    B3    B4             (Bottom Row - Front Territories)
```

**Zone Values & Strategy:**
- **Back Row (T1-T4)**: 900 base banners per territory (doubled value) - highest priority targets
- **Middle Row (M1-M2)**: 450 base banners per territory
- **Front Row (B1-B4)**: 450 base banners per territory - must clear first
- **PLUS**: +10 banners per defensive squad/fleet slot in that territory

**Territory Defense Slots:**
- Number of defensive slots per territory varies by TW
- Depends on participation and matchmaking factors
- Each territory can have different slot counts
- Total conquest value = base banners + (10 × defense slots)

**Attack Progression:**
- Must clear front row (B zones) → middle row (M zones) → back row (T zones)
- Cannot skip tiers
- Back territories worth 2x base value, making them highest priority

#### Attack Phase Mechanics (What We Analyze)
**Banner Scoring System:**

**Offense Victory Bonuses:**
- Base Attack Success: +5 Banners
- First Attempt Victory: +10 Banners (total: 15)
- Second Attempt Victory: +5 Banners (total: 10)
- Survivor Bonus: +1 Banner per surviving unit (max +5)
- Slot Bonus: +1 Banner per empty slot if using <5 units (max +4)
- **Maximum possible**: 64 Banners per attack (first attempt, all survive, optimal conditions)

**Banner Efficiency Concepts:**
- **High Efficiency**: 60+ banners = Clean first attempt win with survivors
- **Medium Efficiency**: 40-59 banners = First attempt but losses, or second attempt with survivors
- **Low Efficiency**: <40 banners = Multiple attempts or heavy losses
- **Banner per Power Ratio**: banners / (squad_power/1000) = efficiency metric

**Attack Strategy Context:**
- Players can only use each unit once (on defense OR offense)
- Failed attacks still "lock" those characters from being used again
- Defensive squads have persistent health/turn meter across attacks
- Coordination matters: feeding turn meter hurts the guild
- Territories must be cleared front-to-back (can't skip ahead)

**Territory Conquest (not in attack logs, but context):**
- +450 Banners per front/middle territory cleared
- +900 Banners per back territory cleared (doubled)
- +10 Banners per defensive squad slot in that territory

**Defense Setting (not in attack logs, but context):**
- Set Squad: +30 Banners
- Set Fleet: +34 Banners

---

### LLM Providers Support

#### Anthropic Claude
- **Default Model**: `claude-3-5-sonnet-20241022`
- **Alternative**: `claude-3-opus-20240229` (more powerful)
- **API Key**: `ANTHROPIC_API_KEY` environment variable
- **Strengths**: Long context, excellent analysis, structured output

#### Google Gemini
- **Default Model**: `gemini-1.5-pro`
- **API Key**: `GOOGLE_API_KEY` environment variable
- **Strengths**: Cost-effective, good for experimentation

### Data Context Strategy

**Token Budget**: ~2000 tokens for context (留足够空间给query和response)

**TW Logs Context**:
```
- Summary statistics (total attacks, banners, players)
- Top 10 performers table
- Guild comparison overview
- Full data available via method call if needed
```

**Guild Data Context**:
```
- Member count and GP summary
- Top GP players
- Activity metrics summary
```

**Player Data Context** (on-demand):
```
- Roster overview
- GL count
- Datacron summary
```

---

## Usage Examples

### Single Query Examples

```bash
# Basic statistics
python swgoh_api_client.py --endpoint ai-query \
  --input-file twlogs.json \
  --ai-query "How many total attacks did we make?"

# Player performance analysis
python swgoh_api_client.py --endpoint ai-query \
  --input-file twlogs.json \
  --ai-query "Who had the best banner efficiency and how does it compare to the average?"

# Strategic analysis
python swgoh_api_client.py --endpoint ai-query \
  --input-file twlogs.json \
  --ai-query "Analyze our attack patterns and identify any weaknesses"

# Comparison queries
python swgoh_api_client.py --endpoint ai-query \
  --input-file twlogs.json \
  --ai-query "Compare our top 5 attackers to opponent's top 5"

# Using Gemini instead
python swgoh_api_client.py --endpoint ai-query \
  --input-file twlogs.json \
  --ai-provider google \
  --ai-query "Give me a summary of this TW"
```

### Interactive Chat Examples

```bash
# Start interactive session
python swgoh_api_client.py --endpoint ai-chat \
  --input-file twlogs.json

# Example conversation:
You: Who attacked the most?
Assistant: Based on the TW logs, [analysis]...

You: What was their banner average?
Assistant: [continues with context from previous question]...

You: Compare them to the guild average
Assistant: [detailed comparison]...
```

---

## Environment Setup

### .env Configuration

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# SWGOH API (existing)
SWGOH_API_KEY=your_api_key_here
SWGOH_DISCORD_ID=your_discord_id_here

# AI Defaults
DEFAULT_AI_PROVIDER=anthropic
DEFAULT_AI_MODEL=claude-3-5-sonnet-20241022
```

---

## File Structure

```
swgoh/
├── swgoh_api_client.py          # Main CLI (existing)
├── swgoh_data_context.py        # NEW: Data loading and summarization
├── swgoh_ai_analyzer.py         # NEW: LangChain AI analyzer
├── swgoh_prompts.py             # NEW: Prompt templates
├── requirements.txt             # Updated with LangChain deps
├── .env                         # Updated with AI API keys
├── README.md                    # Updated with AI features
├── DEVELOPMENT_NOTES.md         # Existing dev docs
├── AI_QA_PROJECT.md            # This file
└── tests/                       # NEW: Test suite
    ├── test_ai_analyzer.py
    ├── test_data_context.py
    └── fixtures/
        └── sample_queries.json
```

---

## Session Progress Log

### Session 1 (2025-11-05)
**Completed**:
- ✅ Read existing documentation (README.md, DEVELOPMENT_NOTES.md)
- ✅ Updated docs with /database endpoint info
- ✅ Explored codebase structure (swgoh_api_client.py, requirements.txt)
- ✅ Designed LangChain-based architecture
- ✅ Created AI_QA_PROJECT.md tracking document
- ✅ Documented TW Attack Phase mechanics (banner scoring, efficiency tiers)
- ✅ Updated DEVELOPMENT_NOTES.md with TW game mechanics

**Key Decisions**:
- Use LangChain for model flexibility
- Claude as primary (Anthropic API), Gemini as secondary
- Focus on Attack Phase analysis (where the data lives)

**Next Session Goals**:
- Update requirements.txt with LangChain dependencies
- Create swgoh_prompts.py with TW-specific system prompts
- Start swgoh_data_context.py implementation
- Test basic LangChain integration

### Session 2 (2025-11-05)
**Completed**:
- ✅ Updated requirements.txt with all LangChain dependencies
- ✅ Created swgoh_prompts.py with comprehensive TW domain knowledge
  - System prompts for TW analysis
  - Domain knowledge (territory map, banner scoring, efficiency tiers)
  - Critical data structure warnings
  - Single-query and chat prompt templates
  - Context formatting functions
- ✅ Created swgoh_data_context.py with full data loading capabilities
  - TW logs parsing (our guild vs opponent)
  - Guild statistics calculation
  - Top performers extraction
  - Player detail lookups
  - Token-aware summarization
- ✅ Created swgoh_ai_analyzer.py with complete LangChain integration
  - Model factory pattern (Anthropic Claude + Google Gemini)
  - Single-query mode
  - Interactive chat mode with conversation history
  - Conversation export functionality
- ✅ Created test_ai_integration.py and verified all imports work
- ✅ Installed all dependencies successfully
- ✅ Updated .env.example with AI API key configuration

**Phase 1 Status**: ✅ COMPLETED

**Next Session Goals**:
- Integrate AI features into swgoh_api_client.py CLI
- Add --endpoint ai-query for single queries
- Add --endpoint ai-chat for interactive mode
- Test with actual TW logs data
- Create usage examples

### Session 3 (2025-11-05)
**Completed**:
- ✅ Added OpenAI support as default provider
  - Added langchain-openai dependency
  - Configured gpt-4o-mini as default (cheapest model)
  - Updated swgoh_ai_analyzer.py with OpenAI model factory
  - Updated CLI to support openai/anthropic/google providers
- ✅ Integrated AI features into swgoh_api_client.py CLI
  - Added --endpoint ai-query for single natural language queries
  - Added --endpoint ai-chat for interactive chat mode
  - Added --ai-provider and --ai-model flags
  - Implemented chat special commands (/clear, /history, /export, /quit)
- ✅ Fixed TW logs parsing in swgoh_data_context.py
  - Updated to handle actual data structure (data vs events array)
  - Fixed nested payload path (payload.zoneData.activityLogMessage)
  - Fixed banner extraction from param array
  - Fixed squad power field name (power vs squadPower)
- ✅ Verified data accuracy
  - AI analysis matches local analyze-tw output perfectly
  - 99 attacks, 1735 banners, 26 players confirmed
  - Created test_tw_parsing.py for verification
- ✅ Tuned system prompt for conciseness
  - Reduced verbosity for simple questions
  - Added examples of good vs bad responses
  - Directive to only elaborate when asked

**Phase 4 Status**: ✅ COMPLETED (CLI Integration)

**Testing Results**:
- ✅ ai-query endpoint working with OpenAI
- ✅ Concise responses (e.g., "99 attacks." for simple questions)
- ✅ Data accuracy verified against local analysis
- ⏳ ai-chat interactive mode (not yet tested)

**Next Session Goals**:
- Test interactive chat mode thoroughly
- Create comprehensive usage examples
- Update README.md with AI features documentation
- Consider Phase 8 advanced features (structured output, multi-file analysis)

---

## Key Decision Log

### Decision 1: Use LangChain
**Date**: 2025-11-05
**Rationale**: Provides model flexibility, built-in memory management, and future extensibility for RAG/agents
**Alternatives Considered**: Direct API integration (less flexible)

### Decision 2: Claude as Primary, Gemini as Secondary
**Date**: 2025-11-05
**Rationale**: User has keys for both; Claude preferred for analysis quality; Gemini for cost-effectiveness
**Alternatives Considered**: OpenAI (no API key available)

### Decision 3: Token-Aware Context Summarization
**Date**: 2025-11-05
**Rationale**: TW logs can be large; need smart summarization to fit in context while maintaining key details
**Implementation**: Build summary (~2000 tokens) with full data available on-demand

---

## Known Issues / Blockers

None currently identified.

---

## Questions / Clarifications Needed

- [ ] What's the typical size of TW log files? (affects summarization strategy)
- [ ] Are there specific analysis patterns used frequently? (can optimize prompts)
- [ ] Should we support multiple file inputs simultaneously? (e.g., TW logs + guild data)
- [ ] Budget/cost constraints for API usage?

---

## Resources

### LangChain Documentation
- [LangChain Docs](https://python.langchain.com/docs/get_started/introduction)
- [Anthropic Integration](https://python.langchain.com/docs/integrations/chat/anthropic)
- [Google Gemini Integration](https://python.langchain.com/docs/integrations/chat/google_generative_ai)
- [Conversation Memory](https://python.langchain.com/docs/modules/memory/)

### SWGOH Context
- [SWGOH Registry Docs](https://github.com/Bhager01/SWGOH-Registry)
- Existing docs in `README.md` and `DEVELOPMENT_NOTES.md`

### API Documentation
- [Anthropic API](https://docs.anthropic.com/)
- [Google AI Studio](https://ai.google.dev/)

---

## Cost Estimates

### Per-Query Cost (Approximate)

**Claude 3.5 Sonnet**:
- Input: $3 per 1M tokens
- Output: $15 per 1M tokens
- Typical query: ~3k input + 500 output = ~$0.02 per query

**Gemini 1.5 Pro**:
- Input: $1.25 per 1M tokens (free tier available)
- Output: $5 per 1M tokens
- Typical query: ~$0.01 per query

**Budget Considerations**:
- 100 queries/day with Claude ≈ $60/month
- 100 queries/day with Gemini ≈ $30/month
- Interactive sessions use more tokens (conversation history)

---

## Success Metrics

- [ ] Can answer 90%+ of common TW analysis questions accurately
- [ ] Response time < 5 seconds for typical queries
- [ ] User can switch models with single flag change
- [ ] Conversation memory works across 10+ turn conversations
- [ ] Documentation enables new users to get started in < 5 minutes
- [ ] Zero errors on well-formed queries
- [ ] Graceful degradation on ambiguous queries

---

## Future Enhancements

### Short-term (Next 2-3 Sessions)
- Multi-file analysis (TW + Guild + Player data together)
- Structured output parsing (JSON responses)
- Query history and favorites

### Medium-term (Future Sprints)
- RAG for large historical datasets
- Custom prompt templates (user-defined)
- Data visualization generation (charts/graphs)
- Automated report generation
- Cost tracking dashboard

### Long-term (Vision)
- Agent-based autonomous analysis
- Predictive analytics (TW outcome predictions)
- Strategy recommendations based on opponent analysis
- Integration with web dashboard
- Real-time analysis during active TWs
