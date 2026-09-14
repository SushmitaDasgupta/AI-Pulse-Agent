#!/usr/bin/env bash
# Remove the macOS weekly LaunchAgent installed by install_macos_weekly_launchd.sh

set -euo pipefail

LABEL="com.aireviewpulsator.weekly"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
rm -f "$PLIST"
echo "Removed LaunchAgent $LABEL (if it was installed)."
