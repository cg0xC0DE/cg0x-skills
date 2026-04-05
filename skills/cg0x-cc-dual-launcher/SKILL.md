---
name: cc-dual-launcher
description: Deploy dual Claude Code provider configurations on Windows, enabling two simultaneous Claude Code instances with different providers via right-click context menus. Trigger whenever the user wants to set up, install, or configure dual/multiple Claude Code providers (e.g., OpenRouter + third-party via CCSwitch), or asks about running Claude Code with different models simultaneously, or wants to add "Claude Code Origin Here" / "Claude Code Switch Here" Windows context menu entries. This is a one-time setup skill — use it when the user asks to deploy or install the dual-launcher setup.
---

# CC Dual Launcher — Skill

Deploys a dual-provider Claude Code setup on Windows, giving you two independent right-click launchers that share the same plugins and marketplace but use different LLM providers.

## How it works

```
cc-origin          →  OpenRouter  ( Opus / Sonnet / any OpenAI-compatible model )
cc-switch          →  CCSwitch   ( third-party, cheap/owned models )
```

- **cc-origin.json** is the single source of truth for the OpenRouter profile (env vars, plugins, marketplaces).
- **cc_switch.bat** does NOT use a settings file — CCSwitch manages `~/.claude/settings.json` externally.
- Both launchers share plugins via `sync_origin_plugins.ps1`, which syncs enabled plugins and marketplaces from the user's existing settings into cc-origin.json.
- **cc-switch.json is not needed** and should not be created.

## Prerequisites

Assumes the following are already available:
- **CCSwitch** installed somewhere
- **OpenRouter account** with API key
- **Claude Code** installed and in PATH

## Phase 1 — Collect configuration

Before writing any files, collect these from the user. Do not assume defaults for credentials.

| Parameter | Prompt | Default |
|-----------|--------|---------|
| `openrouter_key` | OpenRouter API key | (none — required) |
| `openrouter_base_url` | OpenRouter Base URL | `https://openrouter.ai/api` |
| `ccswitch_path` | CCSwitch installation path | `C:\Program Files\CCSwitch\ccswitch.exe` |
| `third_party_model` | Third-party model name | `MiniMax-M2.7` |
| `third_party_base_url` | Third-party Base URL | `https://api.minimax.io/anthropic` |
| `third_party_key` | Third-party API key | (none — required) |
| `proxy_http` | HTTP proxy | (none) |
| `proxy_https` | HTTPS proxy | (none) |
| `install_dir` | Installation directory | `C:\cc-dual-launcher` |
| `origin_default_model` | Default model for cc-origin | `anthropic/claude-4-opus` |

Use `AskUserQuestion` for all of the above. If the user skips a value, apply the default.

## Phase 2 — Create directory structure

Create at `INSTALL_DIR`:

```
INSTALL_DIR/
├── cc_origin.bat
├── cc_switch.bat
├── sync_origin_plugins.ps1
├── cc_launcher.reg
└── profiles/
    └── cc-origin.json
```

Note: **cc-switch.json is NOT needed** — do not create it.

## Phase 3 — Generate files

All files use `{INSTALL_DIR}` as the installation path. In batch files, `%~dp0` (the directory containing the batch file) is used so scripts work regardless of install location.

### `cc_origin.bat`

```bat
@echo off
REM === Claude Code Origin: OpenRouter provider ===
REM All credentials and env config live in profiles\cc-origin.json (single source of truth).
REM --setting-sources "project,local" skips ~/.claude/settings.json (managed by CC Switch).

REM Sync shared settings (plugins etc.) from user settings into cc-origin.json
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync_origin_plugins.ps1"

REM Clear residual env vars that Explorer may inherit
set "ANTHROPIC_API_KEY="

claude --setting-sources "project,local" --settings "%~dp0profiles\cc-origin.json"
```

### `cc_switch.bat`

```bat
@echo off
REM === Claude Code Switch: third-party provider via CC Switch ===
REM CC Switch manages ~/.claude/settings.json automatically.
REM Configure your third-party provider in CC Switch UI before first use.
set "ANTHROPIC_API_KEY="

claude
```

Note: No `--settings` flag — CCSwitch controls the provider externally.

### `sync_origin_plugins.ps1`

```powershell
## Sync shared settings from ~/.claude/settings.json into cc-origin.json
## Called by cc_origin.bat before launching Claude Code
##
## Strategy: copy ALL fields from user settings EXCEPT profile-specific ones (env, model).
## This ensures plugins, permissions, MCP servers, and any future settings stay in sync.

$userSettings = "$env:USERPROFILE\.claude\settings.json"
$originProfile = "$PSScriptRoot\profiles\cc-origin.json"

if (-not (Test-Path $userSettings) -or -not (Test-Path $originProfile)) {
    exit 0
}

$user = Get-Content $userSettings -Raw | ConvertFrom-Json
$origin = Get-Content $originProfile -Raw | ConvertFrom-Json

# Fields that are profile-specific and must NOT be overwritten
$skipFields = @("env", "model")

$changed = $false
foreach ($prop in $user.PSObject.Properties) {
    if ($skipFields -contains $prop.Name) { continue }

    $originVal = $origin.PSObject.Properties[$prop.Name]
    $newJson = $prop.Value | ConvertTo-Json -Depth 10 -Compress
    $oldJson = if ($originVal) { $originVal.Value | ConvertTo-Json -Depth 10 -Compress } else { "" }

    if ($newJson -ne $oldJson) {
        if ($originVal) {
            $originVal.Value = $prop.Value
        } else {
            $origin | Add-Member -NotePropertyName $prop.Name -NotePropertyValue $prop.Value
        }
        $changed = $true
    }
}

if ($changed) {
    $origin | ConvertTo-Json -Depth 10 | Set-Content $originProfile -Encoding UTF8
}
```

### `profiles/cc-origin.json`

Substitute user-provided values into this template. This file is the single source of truth for the OpenRouter profile.

```json
{
    "env":  {
                "ANTHROPIC_AUTH_TOKEN":  "{OPENROUTER_KEY}",
                "ANTHROPIC_BASE_URL":  "{OPENROUTER_BASE_URL}",
                "API_TIMEOUT_MS":  "3000000",
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":  "1"
                {PROXY_JSON_LINES}
            }
}
```

Substitutions:
- `{OPENROUTER_KEY}` → from Phase 1
- `{OPENROUTER_BASE_URL}` → from Phase 1
- `{PROXY_JSON_LINES}` → if proxy provided: `,\n                "HTTP_PROXY":  "{HTTP_PROXY}",\n                "HTTPS_PROXY":  "{HTTPS_PROXY}"`; if none: empty string
- Plugins and marketplaces are NOT included in this template — `sync_origin_plugins.ps1` populates them automatically from the user's existing `~/.claude/settings.json` on first launch

### `cc_launcher.reg`

Replace `{INSTALL_DIR}` with the installation path using `\\` for backslashes.

```reg
Windows Registry Editor Version 5.00

[-HKEY_CLASSES_ROOT\Directory\Background\shell\ClaudeCodeOrigin]
[-HKEY_CLASSES_ROOT\Directory\shell\ClaudeCodeOrigin]
[-HKEY_CLASSES_ROOT\Directory\Background\shell\ClaudeCodeSwitch]
[-HKEY_CLASSES_ROOT\Directory\shell\ClaudeCodeSwitch]

[HKEY_CLASSES_ROOT\Directory\Background\shell\ClaudeCodeOrigin]
@="Claude Code Origin Here"
"Icon"="C:\\Windows\\System32\\cmd.exe"

[HKEY_CLASSES_ROOT\Directory\Background\shell\ClaudeCodeOrigin\command]
@="wt.exe -d \"%V\" --title \"CC Origin: %V\" cmd /k \"{INSTALL_DIR}\\cc_origin.bat\""

[HKEY_CLASSES_ROOT\Directory\shell\ClaudeCodeOrigin]
@="Claude Code Origin Here"
"Icon"="C:\\Windows\\System32\\cmd.exe"

[HKEY_CLASSES_ROOT\Directory\shell\ClaudeCodeOrigin\command]
@="wt.exe -d \"%1\" --title \"CC Origin: %1\" cmd /k \"{INSTALL_DIR}\\cc_origin.bat\""

[HKEY_CLASSES_ROOT\Directory\Background\shell\ClaudeCodeSwitch]
@="Claude Code Switch Here"
"Icon"="C:\\Windows\\System32\\cmd.exe"

[HKEY_CLASSES_ROOT\Directory\Background\shell\ClaudeCodeSwitch\command]
@="wt.exe -d \"%V\" --title \"CC Switch: %V\" cmd /k \"{INSTALL_DIR}\\cc_switch.bat\""

[HKEY_CLASSES_ROOT\Directory\shell\ClaudeCodeSwitch]
@="Claude Code Switch Here"
"Icon"="C:\\Windows\\System32\\cmd.exe"

[HKEY_CLASSES_ROOT\Directory\shell\ClaudeCodeSwitch\command]
@="wt.exe -d \"%1\" --title \"CC Switch: %1\" cmd /k \"{INSTALL_DIR}\\cc_switch.bat\""
```

## Phase 4 — Register context menu (require explicit confirmation)

After writing `cc_launcher.reg`, ask the user:

> "The registry file is ready. Do you want me to merge it now? This adds two right-click entries ('Claude Code Origin Here' and 'Claude Code Switch Here'). You can undo it by deleting the ClaudeCodeOrigin and ClaudeCodeSwitch keys in regedit under HKEY_CLASSES_ROOT\Directory\shell\ and HKEY_CLASSES_ROOT\Directory\Background\shell\."

If the user confirms: run `reg import "{INSTALL_DIR}\cc_launcher.reg"` via Bash. If it fails due to permissions, tell the user to run the command manually in an elevated CMD/PowerShell.

## Phase 5 — Verify

1. List all created files using `Bash find` on `INSTALL_DIR` and confirm each exists
2. Report the final tree, masking credentials:
   - Show only first 8 chars of any API key + `***`
   - Show proxy URLs as `***`

Final structure:
```
{INSTALL_DIR}\
├── cc_origin.bat              ← right-click "Claude Code Origin Here"
├── cc_switch.bat              ← right-click "Claude Code Switch Here"
├── sync_origin_plugins.ps1    ← syncs plugins from user settings
├── cc_launcher.reg            ← context menu registry entries
└── profiles\
    └── cc-origin.json         ← OpenRouter config (single source of truth)
```

Note: **cc-switch.json is intentionally NOT created** — CC Switch manages its own settings externally.

## Notes

- **API keys are credentials** — never log or display full keys. Mask all tokens in output.
- **Backslash handling** — use `%~dp0` in batch files for self-locating paths. Use `\\` in .reg files.
- **CCSwitch is external** — cc_switch.bat passes no credentials; CC Switch must be configured in its own UI before first use.
- **sync_origin_plugins.ps1** runs on every cc-origin launch and silently keeps plugins/marketplaces in sync with the user's main settings. This is normal and expected.
- **The registry only adds entries** — it does not modify or remove any existing Claude Code entries.
