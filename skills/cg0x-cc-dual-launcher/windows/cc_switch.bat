@echo off

REM === Claude Code Switch: Provider managed by CC Switch ===
REM CC Switch manages ~/.claude/settings.json automatically.
REM Switch providers in CC Switch UI, then launch this bat.

REM Sync shared settings (plugins etc.) across all profiles
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync_plugins.ps1"

set "ANTHROPIC_API_KEY="

claude
