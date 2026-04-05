"""
compact_session.py — OpenClaw Session Compaction Tool
Part of cg0x-agent-memory skill: https://github.com/cg0x/cg0x-skills

Compacts oversized OpenClaw session JSONL files into MEMORY.md bullet entries.

Usage (standalone):
    python compact_session.py \\
        --sessions-dir ./agents/main/sessions \\
        --workspace-dir . \\
        --api-key sk-ant-... \\
        --api-url https://api.anthropic.com/v1/messages \\
        --api-type anthropic \\
        --model claude-haiku-4-5 \\
        --agent-name MyAgent
        [--force]

Usage (as library):
    from compact_session import compact_gateway_sessions, check_and_auto_compact
"""

import argparse
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────
COMPACT_THRESHOLD_BYTES = 100 * 1024  # 100 KB
MEMORY_MAX_ENTRIES = 50               # Max bullets in MEMORY.md before archiving
CARRY_OVER_LINES = 10                 # Lines copied to new session for continuity


# ── LLM API Calls ─────────────────────────────────────────────

def _call_anthropic(api_key: str, user_prompt: str,
                    api_url: str, model: str, proxy: str = None) -> str:
    """Call Anthropic Messages API."""
    payload = {
        "model": model,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api_url, data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
    )
    opener = _make_opener(proxy)
    with opener.open(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    for block in result.get("content", []):
        if block.get("type") == "text":
            return block["text"].strip()
    return ""


def _call_openai(api_key: str, user_prompt: str,
                 api_url: str, model: str, proxy: str = None) -> str:
    """Call OpenAI-compatible Chat Completions API."""
    payload = {
        "model": model,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api_url, data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
    )
    opener = _make_opener(proxy)
    with opener.open(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    choices = result.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "").strip()
    return ""


def _make_opener(proxy: str = None):
    if proxy:
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )
    return urllib.request.build_opener()


def call_llm(api_key: str, user_prompt: str, api_url: str,
             api_type: str, model: str, proxy: str = None) -> str:
    """Unified LLM call. api_type: 'anthropic' or 'openai'."""
    if api_type == "anthropic":
        return _call_anthropic(api_key, user_prompt, api_url, model, proxy)
    else:
        return _call_openai(api_key, user_prompt, api_url, model, proxy)


# ── Dialogue Extraction ────────────────────────────────────────

def extract_dialogue(jsonl_path: Path) -> list[dict]:
    """Extract user/assistant turns from a session JSONL. Returns [{role, text}]."""
    dialogue = []
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                if entry.get("type") != "message":
                    continue
                msg = entry.get("message", {})
                role = msg.get("role", "")
                if role not in ("user", "assistant"):
                    continue
                content = msg.get("content", "")
                if isinstance(content, list):
                    parts = [
                        b["text"] for b in content
                        if isinstance(b, dict) and b.get("type") == "text"
                    ]
                    text = "\n".join(parts)
                else:
                    text = str(content)
                text = text.strip()
                if len(text) < 10 or text == "HEARTBEAT_OK":
                    continue
                dialogue.append({"role": role, "text": text[:2000]})
    except Exception:
        pass
    return dialogue


def build_summary_prompt(dialogue: list[dict], agent_name: str) -> str:
    """Build the summarization prompt."""
    convo_text = ""
    for turn in dialogue[-60:]:
        label = "User" if turn["role"] == "user" else agent_name
        convo_text += f"[{label}]: {turn['text'][:500]}\n\n"

    return (
        "You are a memory distillation assistant. Summarize the following "
        "conversation into concise bullet-point memory entries.\n\n"
        "Each entry format:\n"
        "- YYYY-MM-DD · [scene/context] · [people] · [event] · [cause] · [result] · [emotion/impact]\n\n"
        "Rules:\n"
        "- Only record substantive events; skip small talk and repeated heartbeat checks\n"
        "- Keep each entry under 120 characters\n"
        "- Generate at most 10 entries, ordered chronologically\n"
        "- If the conversation has no memorable content, return an empty string\n"
        "- Output ONLY the bullet list, no preamble or explanation\n\n"
        f"Conversation:\n{convo_text}"
    )


# ── MEMORY.md FIFO Management ─────────────────────────────────

def parse_memory_entries(content: str) -> tuple[str, list[str]]:
    """
    Parse MEMORY.md into (header, [bullet_entries]).
    Header is everything before the '## 记忆条目' section.
    """
    SECTION_MARKER = "## 记忆条目"
    if SECTION_MARKER in content:
        idx = content.index(SECTION_MARKER)
        header = content[:idx].rstrip()
        entries_block = content[idx + len(SECTION_MARKER):]
        bullet_entries = [
            l for l in entries_block.split("\n") if l.startswith("- ")
        ]
    else:
        header = content.rstrip()
        bullet_entries = []
    return header, bullet_entries


def archive_old_entries(archive_dir: Path, entries: list[str]) -> None:
    """FIFO-archive overflow entries to memory/archive/YYYY-MM.md."""
    archive_dir.mkdir(parents=True, exist_ok=True)
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    archive_file = archive_dir / f"{month_key}.md"

    existing = archive_file.read_text(encoding="utf-8") if archive_file.exists() else ""
    new_content = existing.rstrip()
    if new_content:
        new_content += "\n"
    new_content += "\n".join(entries) + "\n"
    archive_file.write_text(new_content, encoding="utf-8")


def update_memory_md(memory_path: Path, new_bullets: str) -> int:
    """
    Append new bullet entries to MEMORY.md.
    FIFO-archives to memory/archive/ when entries exceed MEMORY_MAX_ENTRIES.
    Returns current entry count.
    """
    if not new_bullets.strip():
        return 0

    existing = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""
    header, entries = parse_memory_entries(existing)

    new_lines = [l for l in new_bullets.split("\n") if l.startswith("- ")]
    entries.extend(new_lines)

    archive_dir = memory_path.parent / "memory" / "archive"
    if len(entries) > MEMORY_MAX_ENTRIES:
        overflow = entries[: len(entries) - MEMORY_MAX_ENTRIES]
        entries = entries[len(entries) - MEMORY_MAX_ENTRIES:]
        archive_old_entries(archive_dir, overflow)

    content = header + "\n\n## 记忆条目\n\n" + "\n".join(entries) + "\n"
    memory_path.write_text(content, encoding="utf-8")
    return len(entries)


# ── Session Reset ──────────────────────────────────────────────

def reset_session(jsonl_path: Path) -> Path:
    """
    Rename old JSONL to .reset.<timestamp>, create new JSONL with
    the last CARRY_OVER_LINES lines for conversation continuity.
    Returns the path of the new (reset) file.
    """
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
    except Exception:
        return jsonl_path

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S.") + "000Z"
    reset_path = jsonl_path.with_suffix(f".jsonl.reset.{ts}")
    jsonl_path.rename(reset_path)

    carry = all_lines[-CARRY_OVER_LINES:] if len(all_lines) > CARRY_OVER_LINES else all_lines

    session_header = None
    for line in all_lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            entry = json.loads(stripped)
            if entry.get("type") == "session":
                session_header = line if line.endswith("\n") else line + "\n"
                break
        except Exception:
            continue

    with open(jsonl_path, "w", encoding="utf-8") as f:
        if session_header:
            f.write(session_header)
        for line in carry:
            try:
                entry = json.loads(line.strip())
                if entry.get("type") == "session":
                    continue
            except Exception:
                pass
            f.write(line)

    return jsonl_path


# ── Main Compaction Logic ──────────────────────────────────────

def compact_gateway_sessions(
    sessions_dir: str | Path,
    workspace_dir: str | Path,
    api_key: str,
    api_url: str,
    api_type: str = "anthropic",
    model: str = "claude-haiku-4-5",
    agent_name: str = "Agent",
    proxy: str = None,
    force: bool = False,
) -> dict:
    """
    Check and compact all active session JSONL files in sessions_dir.

    Args:
        sessions_dir:  Path to OpenClaw sessions directory (contains *.jsonl)
        workspace_dir: Path to agent workspace (contains MEMORY.md)
        api_key:       LLM API key
        api_url:       LLM API endpoint URL
        api_type:      'anthropic' or 'openai'
        model:         Model ID for summarization
        agent_name:    Agent display name (used in summary prompt)
        proxy:         Optional HTTP proxy URL
        force:         If True, compact regardless of file size

    Returns:
        dict with 'results' list, each entry describing what happened per file.
    """
    sessions_dir = Path(sessions_dir)
    workspace_dir = Path(workspace_dir)
    memory_path = workspace_dir / "MEMORY.md"

    if not sessions_dir.exists():
        return {"error": f"Sessions directory not found: {sessions_dir}"}

    results = []

    for jsonl_file in sessions_dir.glob("*.jsonl"):
        size = jsonl_file.stat().st_size

        if not force and size < COMPACT_THRESHOLD_BYTES:
            results.append({
                "file": jsonl_file.name,
                "size_kb": round(size / 1024, 1),
                "action": "skipped",
                "reason": f"below threshold ({COMPACT_THRESHOLD_BYTES // 1024}KB)",
            })
            continue

        dialogue = extract_dialogue(jsonl_file)
        if len(dialogue) < 4:
            results.append({
                "file": jsonl_file.name,
                "size_kb": round(size / 1024, 1),
                "action": "skipped",
                "reason": "too few dialogue turns to summarize",
            })
            continue

        summary_bullets = ""
        if api_key:
            try:
                prompt = build_summary_prompt(dialogue, agent_name)
                summary_bullets = call_llm(api_key, prompt, api_url, api_type, model, proxy)
            except Exception as e:
                results.append({
                    "file": jsonl_file.name,
                    "size_kb": round(size / 1024, 1),
                    "action": "warn",
                    "reason": f"LLM summary failed: {e}",
                })

        entry_count = 0
        if summary_bullets:
            try:
                entry_count = update_memory_md(memory_path, summary_bullets)
            except Exception as e:
                results.append({
                    "file": jsonl_file.name,
                    "action": "warn",
                    "reason": f"MEMORY.md update failed: {e}",
                })

        try:
            reset_session(jsonl_file)
        except Exception as e:
            results.append({
                "file": jsonl_file.name,
                "action": "error",
                "reason": f"session reset failed: {e}",
            })
            continue

        results.append({
            "file": jsonl_file.name,
            "size_kb": round(size / 1024, 1),
            "action": "compacted",
            "dialogue_turns": len(dialogue),
            "memory_entries": entry_count,
            "summary_generated": bool(summary_bullets),
        })

    return {"results": results}


def check_and_auto_compact(
    sessions_dir: str | Path,
    workspace_dir: str | Path,
    api_key: str,
    api_url: str,
    api_type: str = "anthropic",
    model: str = "claude-haiku-4-5",
    agent_name: str = "Agent",
    proxy: str = None,
) -> list[str]:
    """
    Silently check and compact only sessions exceeding the threshold.
    Suitable for calling from a background thread/scheduler.
    Returns list of compacted filenames.
    """
    sessions_dir = Path(sessions_dir)
    if not sessions_dir.exists():
        return []

    oversized = [
        f for f in sessions_dir.glob("*.jsonl")
        if f.stat().st_size >= COMPACT_THRESHOLD_BYTES
    ]
    if not oversized:
        return []

    result = compact_gateway_sessions(
        sessions_dir=sessions_dir,
        workspace_dir=workspace_dir,
        api_key=api_key,
        api_url=api_url,
        api_type=api_type,
        model=model,
        agent_name=agent_name,
        proxy=proxy,
        force=False,
    )
    return [
        r["file"] for r in result.get("results", [])
        if r.get("action") == "compacted"
    ]


# ── CLI Entry Point ────────────────────────────────────────────

def _parse_args():
    p = argparse.ArgumentParser(
        description="Compact OpenClaw session JSONL files into MEMORY.md entries"
    )
    p.add_argument("--sessions-dir", required=True,
                   help="Path to OpenClaw sessions directory (contains *.jsonl)")
    p.add_argument("--workspace-dir", required=True,
                   help="Path to agent workspace directory (contains MEMORY.md)")
    p.add_argument("--api-key", required=True,
                   help="LLM API key")
    p.add_argument("--api-url", required=True,
                   help="LLM API endpoint URL")
    p.add_argument("--api-type", default="anthropic", choices=["anthropic", "openai"],
                   help="API type: 'anthropic' or 'openai' (default: anthropic)")
    p.add_argument("--model", default="claude-haiku-4-5",
                   help="Model ID for summarization (default: claude-haiku-4-5)")
    p.add_argument("--agent-name", default="Agent",
                   help="Agent display name used in summary prompt")
    p.add_argument("--proxy",
                   help="Optional HTTP proxy URL (e.g. http://127.0.0.1:7890)")
    p.add_argument("--force", action="store_true",
                   help="Compact all sessions regardless of file size")
    return p.parse_args()


def main():
    args = _parse_args()
    result = compact_gateway_sessions(
        sessions_dir=args.sessions_dir,
        workspace_dir=args.workspace_dir,
        api_key=args.api_key,
        api_url=args.api_url,
        api_type=args.api_type,
        model=args.model,
        agent_name=args.agent_name,
        proxy=args.proxy,
        force=args.force,
    )
    for r in result.get("results", []):
        action = r.get("action", "?")
        fname = r.get("file", "?")
        size = r.get("size_kb", "?")
        if action == "compacted":
            entries = r.get("memory_entries", 0)
            turns = r.get("dialogue_turns", 0)
            summarized = "✓" if r.get("summary_generated") else "✗ (no summary)"
            print(f"[compacted] {fname} ({size}KB) → {turns} turns, {entries} memory entries, summary: {summarized}")
        elif action == "skipped":
            print(f"[skipped]   {fname} ({size}KB) — {r.get('reason', '')}")
        elif action == "warn":
            print(f"[warn]      {fname} — {r.get('reason', '')}")
        elif action == "error":
            print(f"[error]     {fname} — {r.get('reason', '')}")

    compacted = [r for r in result.get("results", []) if r.get("action") == "compacted"]
    print(f"\nDone. {len(compacted)} session(s) compacted.")


if __name__ == "__main__":
    main()
