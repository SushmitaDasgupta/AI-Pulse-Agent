#!/usr/bin/env bash
# Install a macOS LaunchAgent that runs the weekly pulse automatically
# every Monday at 14:30 local time (≈ 09:00 UTC when on IST), using this
# repo's .venv + .env — no GitHub secrets required.
#
# Usage (from repo root):
#   ./scripts/install_macos_weekly_launchd.sh
# Uninstall:
#   ./scripts/uninstall_macos_weekly_launchd.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.aireviewpulsator.weekly"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="$ROOT/out/scheduler"
PYTHON="$ROOT/.venv/bin/python"
RUNNER="$ROOT/scripts/run_weekly_pulse.sh"

if [[ ! -x "$PYTHON" ]]; then
  echo "Missing $PYTHON — create the venv and pip install -e . first." >&2
  exit 1
fi

if [[ ! -f "$ROOT/.env" ]]; then
  echo "Missing $ROOT/.env — copy .env.example and fill keys first." >&2
  exit 1
fi

mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"

cat > "$RUNNER" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
export PATH="/usr/local/bin:/opt/homebrew/bin:\$PATH"
# Load .env without printing secrets
set -a
# shellcheck disable=SC1091
source <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ROOT/.env" | sed 's/\r\$//')
set +a
export REQUIRE_MCP="\${REQUIRE_MCP:-true}"
export ACQUIRE_MODE="\${ACQUIRE_MODE:-live}"
exec "$PYTHON" -m src.cli run --require-mcp >>"$LOG_DIR/weekly.log" 2>>"$LOG_DIR/weekly.err"
EOF
chmod +x "$RUNNER"

# Monday = 1 on macOS StartCalendarInterval (Sunday=0)
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${RUNNER}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key>
    <integer>1</integer>
    <key>Hour</key>
    <integer>14</integer>
    <key>Minute</key>
    <integer>30</integer>
  </dict>
  <key>RunAtLoad</key>
  <false/>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/launchd.out</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/launchd.err</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/${LABEL}" 2>/dev/null || true

echo "Installed LaunchAgent: $PLIST"
echo "Schedule: every Monday 14:30 local time → pulsator run --require-mcp"
echo "Logs: $LOG_DIR/weekly.log  and  $LOG_DIR/weekly.err"
echo
echo "Smoke-test now (optional):"
echo "  $RUNNER"
echo
echo "Also keep GitHub Actions secrets set for cloud automation when laptop is off:"
echo "  gh auth refresh -h github.com && ./scripts/setup_github_secrets.sh"
