#!/usr/bin/env bash

# === Claude Code Switch: Provider managed by CC Switch ===
# CC Switch manages ~/.claude/settings.json automatically.
# Switch providers in CC Switch UI, then launch this script.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Sync shared settings (plugins etc.) across all profiles
bash "$SCRIPT_DIR/sync_plugins.sh"

unset ANTHROPIC_API_KEY

claude
