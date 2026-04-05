@echo off

REM === Claude Code Ollama: Local models via Ollama ===
REM Ollama must be running (ollama serve) with the model already pulled.

REM Sync shared settings (plugins etc.) across all profiles
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync_plugins.ps1"

REM Clear residual env vars that Explorer may inherit
set "ANTHROPIC_API_KEY="

REM Change the --model flag to match your pulled model
claude --setting-sources "project,local" --settings "%~dp0profiles\cc-ollama.json"
