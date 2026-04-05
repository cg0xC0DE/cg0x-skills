#!/usr/bin/env bash

# === Claude Code Ollama: Local models via Ollama ===
# Ollama must be running (ollama serve) with the model already pulled.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Sync shared settings (plugins etc.) across all profiles
bash "$SCRIPT_DIR/sync_plugins.sh"

# Clear residual env vars
unset ANTHROPIC_API_KEY

# Change the --model flag to match your pulled model
claude --setting-sources "project,local" --settings "$SCRIPT_DIR/../profiles/cc-ollama.json"
