#!/usr/bin/env bash
## Bidirectional union-merge of shared settings across ALL profiles.
## Called by cc_origin.sh, cc_switch.sh, and cc_ollama.sh before launching Claude Code.
##
## Files synced:
##   1. ~/.claude/settings.json   (used by CC Switch — the "user" settings)
##   2. profiles/cc-origin.json   (used by CC Origin)
##   3. profiles/cc-ollama.json   (used by CC Ollama)
##
## Strategy:
##   - enabledPlugins / extraKnownMarketplaces: UNION across all files (only adds, never deletes).
##   - Other shared fields (permissions, MCP servers, etc.): UNION by key.
##   - Profile-specific fields (env, model): never touched across files.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_SETTINGS="$HOME/.claude/settings.json"
PROFILE_DIR="$SCRIPT_DIR/../profiles"

# Collect all config files that exist
CONFIG_FILES=()
[ -f "$USER_SETTINGS" ] && CONFIG_FILES+=("$USER_SETTINGS")
for f in "$PROFILE_DIR"/*.json; do
    [ -f "$f" ] && CONFIG_FILES+=("$f")
done

if [ ${#CONFIG_FILES[@]} -lt 2 ]; then
    exit 0
fi

# Pass all config file paths to Python for union-merge
python3 - "${CONFIG_FILES[@]}" << 'PYEOF'
import json, sys, copy, os

SKIP_FIELDS = {"env", "model"}
paths = sys.argv[1:]

# Load all configs
configs = {}
for path in paths:
    try:
        with open(path, "r", encoding="utf-8") as f:
            configs[path] = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        continue

if len(configs) < 2:
    sys.exit(0)

def merge_dicts(a, b):
    """Union-merge: all keys from both dicts; a's values take priority on conflict."""
    merged = copy.deepcopy(a)
    for k, v in b.items():
        if k not in merged:
            merged[k] = copy.deepcopy(v)
    return merged

# Collect all shared field names
all_fields = set()
for cfg in configs.values():
    all_fields.update(cfg.keys())

# For each shared field, compute the global union across ALL configs
global_merged = {}
for field in all_fields:
    if field in SKIP_FIELDS:
        continue

    values = [cfg[field] for cfg in configs.values() if field in cfg]
    if not values:
        continue

    # If all values are dicts, union-merge them all
    if all(isinstance(v, dict) for v in values) and len(values) > 1:
        merged = values[0]
        for v in values[1:]:
            merged = merge_dicts(merged, v)
        global_merged[field] = merged
    else:
        # Non-dict: keep first non-None value as reference
        global_merged[field] = values[0]

# Apply the global union back to each config
for path, cfg in configs.items():
    changed = False
    for field, merged_val in global_merged.items():
        existing = cfg.get(field)
        if existing != merged_val:
            cfg[field] = copy.deepcopy(merged_val)
            changed = True

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
            f.write("\n")
PYEOF
