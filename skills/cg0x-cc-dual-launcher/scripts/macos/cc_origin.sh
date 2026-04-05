#!/usr/bin/env bash

# === Claude Code Origin: Native models via OpenRouter ===
# All credentials and env config live in profiles/cc-origin.json (single source of truth).
# --setting-sources "project,local" skips ~/.claude/settings.json (managed by CC Switch).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Sync shared settings (plugins etc.) across all profiles
bash "$SCRIPT_DIR/sync_plugins.sh"

# Clear residual env vars
unset ANTHROPIC_API_KEY

claude --setting-sources "project,local" --settings "$SCRIPT_DIR/../profiles/cc-origin.json"
