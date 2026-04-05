---
name: cg0x-mq-event
description: >
  Guides AI agents on integrating with the local cmd-patrol message queue (MQ) system.
  Provides event publishing patterns for reporting skipped/failed/manual-attention-needed
  items from automated pipelines. Includes endpoint discovery, message schema, and
  ready-to-use Python helper code.
  Use when user asks to "push events", "report errors to MQ", "add event notifications",
  "send alerts to patrol", or when implementing error handling that should surface
  unresolvable items for human attention.
  Triggers: "mq", "消息队列", "事件推送", "push event", "report to patrol", "需要人工处理",
  "跳过的任务", "skipped items", "埋点", "event tracking".
dependencies:
  - name: cmd-patrol
    url: https://github.com/cg0xC0DE/cmd-patrol
    description: >
      Local service management tool that hosts the MQ backend.
      Must be running locally for this skill to function.
    setup: >
      1. Clone: git clone https://github.com/cg0xC0DE/cmd-patrol
      2. Run: start.cmd (auto-creates venv, installs deps, sets CMD_PATROL_URL env var)
      3. Verify: curl http://127.0.0.1:51314/api/mq/stats should return JSON
---

# cmd-patrol MQ Event Integration

## Dependency

This skill **requires** [cmd-patrol](https://github.com/cg0xC0DE/cmd-patrol) to be cloned and running locally.

cmd-patrol's `start.cmd` will:
1. Start the backend on `http://127.0.0.1:51314`
2. Set the `CMD_PATROL_URL` environment variable (both session + persistent via `setx`)

If cmd-patrol is not running, event publishing silently fails (best-effort, never crashes your process).

## Overview

cmd-patrol runs a lightweight local message queue at `http://127.0.0.1:51314`.
When an automated service encounters something it **cannot resolve on its own** — metadata parse errors, missing models, rate limits, validation failures — it should publish an event to this MQ. The human operator reviews and resolves these events via the cmd-patrol web UI.

**When to publish events:**
- An item is **skipped** because of an error the code can't auto-fix
- A resource is **needed** but must be manually acquired (e.g. model download, API key)
- A validation or parse **failure** that requires human judgment
- Any situation where silent failure would cause data loss or missed work

**When NOT to publish events:**
- Transient network errors that will auto-retry successfully
- Normal operational logging (use regular logs for that)
- High-frequency events (> 1 per second) — aggregate first, then publish a summary

## Endpoint Discovery

The MQ endpoint is discovered via environment variable with a hardcoded default:

```
CMD_PATROL_URL  →  defaults to http://127.0.0.1:51314
```

cmd-patrol's `start.cmd` automatically sets this env var (session + persistent).
Other projects read it at runtime via `os.environ.get("CMD_PATROL_URL")` with the above default as fallback.

## Message Schema

```json
{
  "source": "project-name",
  "type": "error_category",
  "title": "Short human-readable summary",
  "detail": "Optional longer description, file paths, error messages, etc.",
  "meta": {}
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `source` | ✅ | Project/service name, e.g. `"civitai-downloader"`, `"link2asr"` |
| `type` | ❌ | Category string, e.g. `"metadata_error"`, `"download_needed"`, `"parse_failure"` |
| `title` | ✅ | Short summary (< 120 chars), shown in UI list |
| `detail` | ❌ | Longer context: file paths, stack traces, URLs, etc. |
| `meta` | ❌ | Arbitrary JSON object for machine-readable data |

## Message States

```
new  ──→  ack  ──→  done
 └──────────────────→ done
```

- **new** — Just published. Human has not seen it yet.
- **ack** — Human has been notified (e.g. via Telegram). Not yet resolved.
- **done** — Human confirms the issue is resolved.

Services only ever create `new` messages. State transitions are handled by the operator.

## Integration Pattern

### Python Helper (copy into your project)

Add this file to your project. It has **zero external dependencies** (stdlib only).

```python
# patrol_mq.py — Publish events to cmd-patrol MQ
import json
import os
import urllib.request

_PATROL_URL = os.environ.get("CMD_PATROL_URL", "http://127.0.0.1:51314")

def publish_event(source: str, title: str, type: str = "", detail: str = "", meta: dict = None):
    """
    Publish an event to cmd-patrol MQ. Fire-and-forget: never raises.
    
    Args:
        source: Your project name, e.g. "civitai-downloader"
        title:  Short summary of what happened
        type:   Category string, e.g. "metadata_error"
        detail: Optional longer description
        meta:   Optional dict with extra structured data
    """
    payload = json.dumps({
        "source": source,
        "type": type,
        "title": title,
        "detail": detail,
        "meta": meta or {},
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            f"{_PATROL_URL}/api/mq/publish",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # MQ is best-effort; never crash the main process
```

### Usage in Application Code

```python
from patrol_mq import publish_event

# Example: metadata parse failure
try:
    metadata = parse_exif(image_path)
except ExifError as e:
    publish_event(
        source="civitai-downloader",
        type="metadata_error",
        title=f"EXIF parse failed: {image_path.name}",
        detail=f"File: {image_path}\nError: {e}",
        meta={"file": str(image_path), "error_type": type(e).__name__}
    )
    # continue processing other files...

# Example: model download needed
if not model_path.exists():
    publish_event(
        source="civitai-downloader",
        type="download_needed",
        title=f"Model missing: {model_name}",
        detail=f"Expected at: {model_path}\nCivitAI URL: {model_url}",
        meta={"model": model_name, "url": model_url}
    )

# Example: rate limit hit, batch skipped
publish_event(
    source="link2asr",
    type="rate_limit",
    title=f"API rate limit, {skipped_count} items skipped",
    detail=f"Skipped IDs: {skipped_ids[:20]}",
    meta={"count": skipped_count}
)
```

### cURL / Batch Script

```bash
curl -s -X POST http://127.0.0.1:51314/api/mq/publish \
  -H "Content-Type: application/json" \
  -d '{"source":"my-script","type":"error","title":"Something failed","detail":"..."}'
```

### Node.js / JavaScript

```javascript
async function publishEvent(source, title, type = '', detail = '', meta = {}) {
    const url = (process.env.CMD_PATROL_URL || 'http://127.0.0.1:51314') + '/api/mq/publish';
    try {
        await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source, type, title, detail, meta }),
        });
    } catch (e) { /* best-effort */ }
}
```

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mq/publish` | POST | Publish a new event (JSON body) |
| `/api/mq/messages?status=new&source=xxx` | GET | Query messages with filters |
| `/api/mq/messages/<id>/ack` | POST | Mark as acknowledged |
| `/api/mq/messages/<id>/done` | POST | Mark as resolved |
| `/api/mq/batch-done` | POST | `{"before_id":"..."}` — resolve this and all older messages |
| `/api/mq/batch-ack` | POST | Mark all `new` → `ack` |
| `/api/mq/stats` | GET | `{new, ack, done, total}` counts |

## Best Practices

1. **`source` should be stable** — use the project name, not a filename or function name
2. **`title` should be actionable** — "Model X missing" not "Error occurred"
3. **`detail` should help the human resolve it** — include file paths, URLs, IDs
4. **`meta` is for programmatic use** — put structured data here for potential automation
5. **Never let MQ failure crash your process** — always wrap in try/except, the helper does this already
6. **Deduplicate before publishing** — if the same error recurs in a loop, publish once with a count, not once per iteration
