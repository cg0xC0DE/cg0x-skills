#!/usr/bin/env bash
#
# Install macOS Quick Actions (Automator Services) for cc-dual-launcher.
# After running this script, right-click any folder in Finder →
#   Quick Actions → "CC Origin Here" / "CC Ollama Here" / "CC Switch Here"
#
# Usage: bash install_services.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICES_DIR="$HOME/Library/Services"
mkdir -p "$SERVICES_DIR"

# ── helper: create one Quick Action ──────────────────────────────────────────
create_service() {
    local name="$1"      # display name, e.g. "CC Origin Here"
    local launcher="$2"  # script to run, e.g. cc_origin.sh
    local workflow_dir="$SERVICES_DIR/${name}.workflow/Contents"

    mkdir -p "$workflow_dir"
    cat > "$workflow_dir/document.wflow" << WFLOW_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>AMBundleVersion</key>
	<integer>2</integer>
	<key>AMApplicationBuild</key>
	<string>523</string>
	<key>AMApplicationVersion</key>
	<string>2.10</string>
	<key>NSUserActivityTypes</key>
	<array/>
	<key>actions</key>
	<array>
		<dict>
			<key>action</key>
			<dict>
				<key>AMAccepts</key>
				<dict>
					<key>Container</key>
					<string>List</string>
					<key>Optional</key>
					<true/>
					<key>Types</key>
					<array>
						<string>com.apple.cocoa.path</string>
					</array>
				</dict>
				<key>AMActionVersion</key>
				<string>1.0.2</string>
				<key>AMApplication</key>
				<array>
					<string>Automator</string>
				</array>
				<key>AMCategory</key>
				<string>AMCategoryUtilities</string>
				<key>AMIconName</key>
				<string>Automator</string>
				<key>AMKeywords</key>
				<array>
					<string>Shell</string>
					<string>Script</string>
					<string>Command</string>
					<string>Run</string>
				</array>
				<key>AMName</key>
				<string>Run Shell Script</string>
				<key>AMProvides</key>
				<dict>
					<key>Container</key>
					<string>List</string>
					<key>Types</key>
					<array>
						<string>com.apple.cocoa.string</string>
					</array>
				</dict>
				<key>AMRequiredResources</key>
				<array/>
				<key>AMTag</key>
				<string>AMTagUtilities</string>
				<key>ActionBundlePath</key>
				<string>/System/Library/Automator/Run Shell Script.action</string>
				<key>ActionName</key>
				<string>Run Shell Script</string>
				<key>BundleIdentifier</key>
				<string>com.apple.RunShellScript</string>
				<key>CFBundleVersion</key>
				<string>1.0.2</string>
				<key>CanShowSelectedItemsWhenRun</key>
				<false/>
				<key>CanShowWhenRun</key>
				<true/>
				<key>InputFailedAction</key>
				<string>SkipAction</string>
				<key>Parameters</key>
				<dict>
					<key>COMMAND_STRING</key>
					<string>cd "\$1"
open -a Terminal "\$SHELL" -c "cd '\$1' &amp;&amp; bash '${SCRIPT_DIR}/${launcher}'; exec \$SHELL"</string>
					<key>CheckedForUserDefaultShell</key>
					<true/>
					<key>inputMethod</key>
					<integer>1</integer>
					<key>shell</key>
					<string>/bin/bash</string>
					<key>source</key>
					<string></string>
				</dict>
			</dict>
			<key>isViewVisible</key>
			<integer>1</integer>
		</dict>
	</array>
	<key>connectors</key>
	<dict/>
	<key>workflowMetaData</key>
	<dict>
		<key>applicationBundleIDsByPath</key>
		<dict/>
		<key>applicationPaths</key>
		<array/>
		<key>inputTypeIdentifier</key>
		<string>com.apple.Automator.fileSystemObject.folder</string>
		<key>outputTypeIdentifier</key>
		<string>com.apple.Automator.nothing</string>
		<key>presentationMode</key>
		<integer>11</integer>
		<key>processesInput</key>
		<integer>0</integer>
		<key>serviceApplicationPath</key>
		<string></string>
		<key>serviceInputTypeIdentifier</key>
		<string>com.apple.Automator.fileSystemObject.folder</string>
		<key>serviceOutputTypeIdentifier</key>
		<string>com.apple.Automator.nothing</string>
		<key>workflowTypeIdentifier</key>
		<string>com.apple.Automator.servicesMenu</string>
	</dict>
</dict>
</plist>
WFLOW_EOF

    echo "  ✓ Installed: $name"
}

# ── install all three services ───────────────────────────────────────────────
echo "Installing Quick Actions to $SERVICES_DIR ..."
create_service "CC Origin Here"  "cc_origin.sh"
create_service "CC Ollama Here"  "cc_ollama.sh"
create_service "CC Switch Here"  "cc_switch.sh"

# ── ensure launcher scripts are executable ───────────────────────────────────
chmod +x "$SCRIPT_DIR/cc_origin.sh" "$SCRIPT_DIR/cc_ollama.sh" "$SCRIPT_DIR/cc_switch.sh" "$SCRIPT_DIR/sync_plugins.sh"

echo ""
echo "Done! Right-click any folder in Finder → Quick Actions to see:"
echo "  • CC Origin Here   (OpenRouter)"
echo "  • CC Ollama Here   (Ollama local models)"
echo "  • CC Switch Here   (CC Switch)"
echo ""
echo "If they don't appear, go to System Settings → Privacy & Security → Extensions → Finder"
echo "and make sure the services are enabled."
