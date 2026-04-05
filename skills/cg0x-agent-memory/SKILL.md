---
name: cg0x-agent-memory
description: >
  Patches OpenClaw's minimal session memory with a three-tier memory system:
  short-term (active session JSONL), mid-term (MEMORY.md bullet summaries),
  and long-term (FIFO-archived monthly files). Prevents token overflow by
  auto-compacting sessions over 100KB using an LLM summary, then resetting
  the session while carrying over the last 10 lines for continuity.
  Use when the user wants the agent to "remember things across sessions",
  "not forget past conversations", "reduce token costs", "compact session",
  "build a memory system", or when session files are growing too large.
  Triggers: "记忆", "memory", "session压缩", "compact session", "忘记了",
  "跨session记忆", "token overflow", "会话太长", "MEMORY.md", "归档记忆".
---

# cg0x-agent-memory

A drop-in memory patch for OpenClaw agents. Adds a three-tier memory system
that keeps sessions lean, preserves important context across resets, and
provides on-demand deep memory search.

## The Problem

OpenClaw feeds the entire session JSONL to the LLM on every turn. Sessions
grow unboundedly — a 700KB session means ~500K tokens of context on every
heartbeat. OpenClaw's built-in `safeguard` compaction resets the session but
**does not summarize** what happened. Context is lost.

## The Solution: Three-Tier Memory

```
┌─────────────────────────────────────────────────────────┐
│  Tier 1 · Session (short-term)                          │
│  Active JSONL file managed by OpenClaw                  │
│  Auto-compacted when > 100KB                            │
├─────────────────────────────────────────────────────────┤
│  Tier 2 · MEMORY.md (mid-term)                          │
│  Bullet-list summaries, injected into every session     │
│  Format: date · scene · people · event · cause ·        │
│          result · emotion/impact                        │
│  Max 50 entries (FIFO overflow → Tier 3)                │
├─────────────────────────────────────────────────────────┤
│  Tier 3 · memory/archive/YYYY-MM.md (long-term)         │
│  FIFO-archived old entries, NOT loaded automatically    │
│  Query on demand: python query_deep_memory.py <keyword> │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Setup (Agent: read and execute these steps)

### Step 1 — Copy tools to your workspace

Copy the two tool files from this skill into your workspace directory:

```
your-workspace/
├── compact_session.py      ← from tools/compact_session.py
├── query_deep_memory.py    ← from tools/query_deep_memory.py
└── MEMORY.md               ← create if not exists
```

### Step 2 — Create or update MEMORY.md

If `MEMORY.md` does not exist, create it with this structure:

```markdown
# MEMORY.md — [Agent Name]'s Long-Term Memory

## About the User
- (fill in key facts about the user: timezone, preferred name, communication style)

## Important Agreements
- (fill in standing rules, preferences, recurring context)

## 记忆条目

```

The `## 记忆条目` section is managed automatically by `compact_session.py`.
**Never delete this heading** — the tool uses it as an anchor.

### Step 3 — Update AGENTS.md (or equivalent system prompt file)

Add this Memory section to your agent's workspace definition:

```markdown
## Memory

Three-tier memory system:

- **Session (short-term)** — active conversation history managed by OpenClaw,
  auto-compacted when > 100KB
- **`MEMORY.md` (mid-term)** — bullet summaries, format:
  `date · scene · people · event · cause · result · emotion/impact`,
  max 50 entries, maintained automatically
- **`memory/archive/YYYY-MM.md` (long-term)** — FIFO archive, not loaded
  automatically; search with: `python query_deep_memory.py <keyword>`

Read `MEMORY.md` at the start of every **main session** (direct chat).
Do NOT load it in group/shared contexts (security).
To remember something: write it to `MEMORY.md`.
"Mental notes" don't survive session resets.
```

### Step 4 — Configure the backend trigger (optional but recommended)

If you have a backend service managing the gateway, call `compact_session.py`
automatically when sessions exceed the threshold:

```python
from compact_session import compact_gateway_sessions, check_and_auto_compact

# Manual: compact all oversized sessions for a gateway
result = compact_gateway_sessions(
    sessions_dir="/path/to/agents/main/sessions",
    workspace_dir="/path/to/workspace",
    api_key="your-anthropic-key",   # or any OpenAI-compatible key
    api_url="https://api.anthropic.com/v1/messages",
    api_type="anthropic",           # "anthropic" or "openai"
    model="claude-haiku-4-5",
    agent_name="MyAgent",
)

# Auto: check and compact only if threshold exceeded
check_and_auto_compact(
    sessions_dir=..., workspace_dir=..., api_key=..., ...
)
```

---

## Tool Reference

### compact_session.py

Compacts oversized session JSONL files:

1. Reads the session JSONL and extracts `user`/`assistant` dialogue turns
2. Calls an LLM to generate bullet-list memory entries
3. Appends entries to `MEMORY.md` under `## 记忆条目`
4. If entries exceed 50, FIFO-archives oldest to `memory/archive/YYYY-MM.md`
5. Renames the old JSONL to `<name>.jsonl.reset.<timestamp>`
6. Creates a new JSONL with the last 10 lines of the old session (continuity)

**Standalone usage** (agent calls this directly):

```bash
# Compact all sessions in a directory (threshold check)
python compact_session.py \
  --sessions-dir ./agents/main/sessions \
  --workspace-dir . \
  --api-key sk-ant-... \
  --api-url https://api.anthropic.com/v1/messages \
  --api-type anthropic \
  --model claude-haiku-4-5 \
  --agent-name MyAgent

# Force compact regardless of file size
python compact_session.py ... --force
```

**Key constants** (edit at top of file to customize):

| Constant | Default | Meaning |
|----------|---------|---------|
| `COMPACT_THRESHOLD_BYTES` | `102400` | 100KB — trigger size |
| `MEMORY_MAX_ENTRIES` | `50` | Max bullets in MEMORY.md before archiving |
| `CARRY_OVER_LINES` | `10` | Lines copied to new session for continuity |

### query_deep_memory.py

Searches archived memory entries in `memory/archive/`:

```bash
# Search for entries containing all keywords
python query_deep_memory.py 旅行 上海

# Returns up to 20 matching lines, newest month first
```

**When to use**: Only when the user explicitly asks you to recall something
you've forgotten, and it's not in `MEMORY.md`. Do not call proactively.

---

## Memory Entry Format

Each entry follows this structure (all fields separated by ` · `):

```
- YYYY-MM-DD · [scene/context] · [people] · [event] · [cause] · [result] · [emotion/impact]
```

Examples:
```
- 2026-02-19 · group chat · user, agent · discussed weather · user asked · provided Shanghai forecast 8-14°C · light humor
- 2026-02-19 · DM · user · user asked to stop heartbeat replies · user felt interrupted · agent adjusted behavior · improved relationship
- 2026-01-15 · DM · user · user shared project deadline · upcoming demo · agreed to prioritize frontend polish · mild stress noted
```

Entries without a clear date should start with `无日期` instead.

---

## LLM Provider Compatibility

`compact_session.py` supports two API types:

| Provider | `--api-type` | `--api-url` | Key format |
|----------|-------------|-------------|------------|
| Anthropic | `anthropic` | `https://api.anthropic.com/v1/messages` | `sk-ant-...` |
| OpenAI / compatible | `openai` | `https://api.openai.com/v1/chat/completions` | `sk-...` |

Use the cheapest model available — summaries are short and don't require
reasoning. Recommended: `claude-haiku-4-5`, `gpt-4o-mini`, `moonshot-v1-8k`.

---

## File Layout After Setup

```
workspace/
├── AGENTS.md                    ← updated with Memory section
├── MEMORY.md                    ← mid-term memory (auto-managed)
├── compact_session.py           ← compaction tool
├── query_deep_memory.py         ← deep search tool
└── memory/
    └── archive/
        ├── 2026-01.md           ← FIFO-archived old entries
        └── 2026-02.md
```

---

## Trigger Keywords

Agent should activate this skill when the user says:
- "帮我建立记忆系统" / "set up memory"
- "session 太长了" / "token overflow"
- "你忘记了..." / "you forgot..."
- "压缩一下会话" / "compact session"
- "把这个记下来" / "remember this"
- "查一下以前..." / "look up past..."
