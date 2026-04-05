## Bidirectional union-merge of shared settings across ALL profiles.
## Called by cc_origin.bat, cc_switch.bat, and cc_ollama.bat before launching Claude Code.
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

$profileDir = Join-Path $PSScriptRoot "profiles"
$userSettings = "$env:USERPROFILE\.claude\settings.json"

# Collect all config files that exist
$configFiles = @()
if (Test-Path $userSettings)               { $configFiles += $userSettings }
$profileJsons = Get-ChildItem $profileDir -Filter "*.json" -ErrorAction SilentlyContinue
foreach ($f in $profileJsons) { $configFiles += $f.FullName }

if ($configFiles.Count -lt 2) { exit 0 }

# Fields that are profile-specific and must NOT be synced
$skipFields = @("env", "model")

# Load all configs
$configs = @{}
foreach ($path in $configFiles) {
    $configs[$path] = Get-Content $path -Raw | ConvertFrom-Json
}

# ── helper: union-merge two PSObjects (top-level keys only) ──
function Merge-Objects ($a, $b) {
    if ($null -eq $a) { return $b }
    if ($null -eq $b) { return $a }
    $merged = $a.PSObject.Copy()
    foreach ($prop in $b.PSObject.Properties) {
        if (-not $merged.PSObject.Properties[$prop.Name]) {
            $merged | Add-Member -NotePropertyName $prop.Name -NotePropertyValue $prop.Value
        }
    }
    return $merged
}

# ── collect the global union of all shared fields ──
$allFields = @{}
foreach ($path in $configFiles) {
    foreach ($prop in $configs[$path].PSObject.Properties) {
        $allFields[$prop.Name] = $true
    }
}

# ── for each shared field, compute the union across ALL configs ──
$globalMerged = @{}
foreach ($field in $allFields.Keys) {
    if ($skipFields -contains $field) { continue }

    # Collect all values for this field
    $values = @()
    foreach ($path in $configFiles) {
        $val = $configs[$path].PSObject.Properties[$field]
        if ($val) { $values += $val.Value }
    }

    if ($values.Count -eq 0) { continue }

    # If all values are PSObjects, union-merge them all
    $allObjects = $true
    foreach ($v in $values) {
        if ($v -isnot [System.Management.Automation.PSCustomObject]) {
            $allObjects = $false; break
        }
    }

    if ($allObjects -and $values.Count -gt 1) {
        $merged = $values[0]
        for ($i = 1; $i -lt $values.Count; $i++) {
            $merged = Merge-Objects $merged $values[$i]
        }
        $globalMerged[$field] = $merged
    } else {
        # Non-object field: keep first non-null value as reference (no cross-copy for scalars)
        $globalMerged[$field] = $values[0]
    }
}

# ── apply the global union back to each config ──
$changed = @{}
foreach ($path in $configFiles) { $changed[$path] = $false }

foreach ($field in $globalMerged.Keys) {
    $mergedVal = $globalMerged[$field]
    $mergedJson = $mergedVal | ConvertTo-Json -Depth 10 -Compress

    foreach ($path in $configFiles) {
        $existing = $configs[$path].PSObject.Properties[$field]
        $existingJson = if ($existing) { $existing.Value | ConvertTo-Json -Depth 10 -Compress } else { "" }

        if ($existingJson -ne $mergedJson) {
            if ($existing) {
                $existing.Value = $mergedVal
            } else {
                $configs[$path] | Add-Member -NotePropertyName $field -NotePropertyValue $mergedVal
            }
            $changed[$path] = $true
        }
    }
}

# ── write back only changed files ──
foreach ($path in $configFiles) {
    if ($changed[$path]) {
        $configs[$path] | ConvertTo-Json -Depth 10 | Set-Content $path -Encoding UTF8
    }
}
