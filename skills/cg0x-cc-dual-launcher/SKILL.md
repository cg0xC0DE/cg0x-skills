---
name: cg0x-cc-dual-launcher
description: >
  Deploy multi-provider Claude Code setups on Windows and macOS. Supports three
  simultaneous profiles — OpenRouter (origin), CC Switch (third-party), and Ollama
  (local) — each with independent right-click / Quick Action launchers that share
  plugins and marketplaces via automatic sync. Trigger when the user wants to set up,
  install, or configure multiple Claude Code providers, or asks about running Claude
  Code with different models simultaneously.
---

# CC Multi-Launcher — Skill

Deploys a multi-provider Claude Code setup on **Windows** and **macOS**, giving you three independent launchers that share the same plugins and marketplace but use different LLM providers.

## Three Profiles

```
cc-origin   →  OpenRouter    ( Opus / Sonnet / any OpenRouter model )
cc-switch   →  CC Switch     ( third-party provider managed externally )
cc-ollama   →  Ollama        ( local models, fully offline )
```

## How It Works

- Each profile has its own JSON config in `profiles/` containing **only** `env` (credentials).
- `sync_plugins` runs before every launch and **union-merges** `enabledPlugins`, `extraKnownMarketplaces`, `permissions`, and all other shared fields across **all** profile JSONs + `~/.claude/settings.json`. Profile-specific fields (`env`, `model`) are never touched.
- **cc-switch** does NOT use a settings file — CC Switch manages `~/.claude/settings.json` externally.

## Ready-to-Use Scripts

All scripts are in `windows/` and `macos/` directories with identical structure:

```
windows/                              macos/
├── cc_origin.bat                     ├── cc_origin.sh
├── cc_switch.bat                     ├── cc_switch.sh
├── cc_ollama.bat                     ├── cc_ollama.sh
├── sync_plugins.ps1                  ├── sync_plugins.sh
├── context_menu.reg.template         ├── install_services.sh
└── profiles/                         └── profiles/
    ├── cc-origin.json.template           ├── cc-origin.json.template
    └── cc-ollama.json.template           └── cc-ollama.json.template
```

## Installation

### Phase 1 — Choose install directory and copy scripts

Pick a permanent location and copy the platform scripts there:

| Platform | Default install dir | Source |
|----------|-------------------|--------|
| Windows  | `C:\cc-dual-launcher` | `windows/` |
| macOS    | `~/cc-dual-launcher` | `macos/` |

### Phase 2 — Collect credentials

Before creating profiles, collect these from the user. Do not assume defaults for credentials.

| Parameter | Prompt | Default |
|-----------|--------|---------|
| `openrouter_key` | OpenRouter API key | (none — required) |
| `openrouter_base_url` | OpenRouter Base URL | `https://openrouter.ai/api` |
| `ollama_model` | Ollama model name | (none — user must specify) |
| `proxy_http` | HTTP proxy | (none) |
| `proxy_https` | HTTPS proxy | (none) |

### Phase 3 — Create profile JSONs from templates

Copy `.template` files to `.json` and substitute user values:

- `profiles/cc-origin.json.template` → `profiles/cc-origin.json`
  - Replace `{OPENROUTER_API_KEY}` with user's key
  - Replace `{OPENROUTER_BASE_URL|...}` with user's URL (or use the default after `|`)
  - Add proxy env vars if provided

- `profiles/cc-ollama.json.template` → `profiles/cc-ollama.json`
  - Usually no changes needed (defaults to `http://localhost:11434`)

**No profile JSON is needed for cc-switch** — CC Switch manages `~/.claude/settings.json` externally.

### Phase 4 — Register launchers

**Windows:** Generate `context_menu.reg` from `context_menu.reg.template` by replacing `{INSTALL_DIR}` with the actual path using `\\` backslashes. Then:

```
reg import "C:\cc-dual-launcher\context_menu.reg"
```

Ask the user for explicit confirmation before importing. If it fails, tell the user to run in an elevated CMD.

**macOS:** Run the installer script:

```bash
bash ~/cc-dual-launcher/install_services.sh
```

This creates Finder Quick Actions: right-click any folder → Quick Actions → "CC Origin Here" / "CC Ollama Here" / "CC Switch Here".

### Phase 5 — Verify

1. List all created files and confirm each exists
2. Report the final tree, masking credentials (show only first 8 chars of any API key + `***`)
3. Test: run each launcher script once to confirm sync_plugins runs without errors

## Notes

- **API keys are credentials** — never log or display full keys. Mask all tokens in output.
- **Backslash handling** — use `%~dp0` in Windows bat files for self-locating paths. Use `\\` in .reg files.
- **CC Switch is external** — cc_switch does not pass credentials; CC Switch must be configured in its own UI before first use.
- **sync_plugins** runs on every launch and silently keeps plugins/marketplaces/permissions in sync across all profiles + user settings. This is normal and expected.
- **The registry only adds entries** — it does not modify or remove any existing Claude Code entries.
- **Ollama** must be running (`ollama serve`) with the model already pulled before launching cc_ollama.
