# shared settings for the APEXLang round-trip scripts
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONN="${APEX_CONN:-docker-demo}"
APP_ID="${APEX_APP_ID:-102}"
WORKSPACE="${APEX_WORKSPACE:-DEMO}"
APP_DIR="$ROOT/applications/ut"
