#!/usr/bin/env bash
# Create or reset the disposable consumer app used by `scripts/theme.sh release`: (re)imports
# tests/live/consumer-apps/minimal as app 9010 (alias TF-CONSUMER-MINIMAL-9010). Refuses an ID outside
# 9000-9099 and an ID that belongs to any other app.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/tests/live/consumer-apps/minimal"
conn="docker-demo"; workspace="DEMO"; app_id="9010"; yes=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --connection) conn="$2"; shift 2;;
    --workspace) workspace="$2"; shift 2;;
    --app-id) app_id="$2"; shift 2;;
    --yes) yes=1; shift;;
    *) echo "usage: reset-consumer.sh [--connection NAME] [--workspace WS] [--app-id 9010] [--yes]" >&2; exit 2;;
  esac
done
if [[ ! "$app_id" =~ ^[0-9]+$ ]] || (( app_id < 9000 || app_id > 9099 )); then
  echo "reset-consumer: app id must be in the disposable range 9000-9099 (got $app_id)" >&2; exit 2
fi
alias="TF-CONSUMER-MINIMAL-$app_id"

existing=$(sql -S -name "$conn" <<SQL
set heading off feedback off pagesize 0 verify off
/* CONSUMER_EXISTING_QUERY */
select application_id || '|' || alias from apex_applications where application_id in ($app_id);
exit
SQL
)
current_alias=$(grep -E "^[[:space:]]*$app_id\|" <<<"$existing" | head -1 | cut -d'|' -f2 | tr -d '[:space:]' || true)
if [[ -n "$current_alias" && "${current_alias^^}" != "$alias" ]]; then
  echo "reset-consumer: app $app_id is $current_alias, not $alias - refusing to overwrite it" >&2; exit 1
fi
if [[ $yes -ne 1 ]]; then
  read -r -p "(Re)import the clean consumer into app $app_id ($alias)? [y/N] " answer
  [[ "$answer" =~ ^[yY]$ ]] || { echo "aborted"; exit 1; }
fi

# A failed `apex validate` does not stop a SQLcl script (pitfalls §4.4), so gate on its text first.
out=$(sql -S -name "$conn" <<SQL
apex validate -input $SRC -workspace $workspace
exit
SQL
)
grep -qi "validation.*successful" <<<"$out" || { echo "$out" >&2; echo "reset-consumer: validation failed - nothing imported" >&2; exit 1; }
sql -S -name "$conn" <<SQL
whenever sqlerror exit failure
apex import -input $SRC -workspace $workspace -id $app_id -alias $alias -name "Theme Factory Minimal Consumer"
exit
SQL
echo "CONSUMER app=$app_id alias=$alias status=RESET"
