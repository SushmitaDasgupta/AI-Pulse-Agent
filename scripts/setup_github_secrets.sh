#!/usr/bin/env bash
# One-time setup: copy Pulsator .env values into GitHub Actions secrets
# so the Monday Weekly Pulse cron can run unattended.
#
# Prerequisites:
#   gh auth login   # or: gh auth refresh -h github.com
#   .env filled with GROQ_API_KEY, GEMINI_API_KEY, GOOGLE_DOCS_DOCUMENT_ID, EMAIL_TO
#
# Usage (from repo root):
#   ./scripts/setup_github_secrets.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v gh >/dev/null 2>&1; then
  echo "Install GitHub CLI: https://cli.github.com/" >&2
  exit 1
fi

if ! gh auth status -h github.com >/dev/null 2>&1; then
  echo "GitHub CLI is not authenticated. Run:" >&2
  echo "  gh auth refresh -h github.com" >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Missing .env — copy .env.example and fill keys first." >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a
# shellcheck disable=SC1091
source <(grep -E '^(GROQ_API_KEY|GEMINI_API_KEY|GOOGLE_DOCS_DOCUMENT_ID|EMAIL_TO|MCP_SERVER_URL|MCP_API_KEY|ACQUIRE_MAX_REVIEWS)=' .env | sed 's/\r$//')
set +a

required=(GROQ_API_KEY GEMINI_API_KEY GOOGLE_DOCS_DOCUMENT_ID EMAIL_TO)
missing=0
for key in "${required[@]}"; do
  if [[ -z "${!key:-}" ]]; then
    echo "Missing in .env: $key" >&2
    missing=1
  fi
done
if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

echo "Setting GitHub Actions secrets on $(gh repo view --json nameWithOwner -q .nameWithOwner) ..."

gh secret set GROQ_API_KEY --body "$GROQ_API_KEY"
gh secret set GEMINI_API_KEY --body "$GEMINI_API_KEY"
gh secret set GOOGLE_DOCS_DOCUMENT_ID --body "$GOOGLE_DOCS_DOCUMENT_ID"
gh secret set EMAIL_TO --body "$EMAIL_TO"

if [[ -n "${MCP_SERVER_URL:-}" ]]; then
  # Ensure /mcp suffix for the Streamable HTTP endpoint
  mcp_url="$MCP_SERVER_URL"
  if [[ "$mcp_url" != */mcp ]]; then
    mcp_url="${mcp_url%/}/mcp"
  fi
  gh secret set MCP_SERVER_URL --body "$mcp_url"
fi
if [[ -n "${MCP_API_KEY:-}" ]]; then
  gh secret set MCP_API_KEY --body "$MCP_API_KEY"
fi
if [[ -n "${ACQUIRE_MAX_REVIEWS:-}" ]]; then
  gh secret set ACQUIRE_MAX_REVIEWS --body "$ACQUIRE_MAX_REVIEWS"
fi

# Ensure the workflow is enabled (schedules do nothing if disabled)
gh workflow enable "Weekly Pulse" 2>/dev/null || true

echo
echo "Done. Automation:"
echo "  • Cron: Mondays 09:00 UTC → full pulsator run (Doc append + Gmail draft)"
echo "  • Manual: gh workflow run \"Weekly Pulse\" -f acquire_mode=file -f require_mcp=true"
echo
echo "Verify: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/actions/workflows/weekly-pulse.yml"
