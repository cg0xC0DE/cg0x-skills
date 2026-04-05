@echo off

REM === Claude Code Origin: Native models via OpenRouter ===
REM All credentials and env config live in profiles\cc-origin.json (single source of truth).
REM --setting-sources "project,local" skips ~/.claude/settings.json (managed by CC Switch).

REM Sync shared settings (plugins etc.) across all profiles
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync_plugins.ps1"

REM Clear residual env vars that Explorer may inherit
set "ANTHROPIC_API_KEY="

claude --setting-sources "project,local" --settings "%~dp0..\profiles\cc-origin.json"
