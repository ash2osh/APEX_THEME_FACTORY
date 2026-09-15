#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage: provision-consumer-fixtures.sh --connection <conn> --workspace <ws> [options]

Options:
  --connection <name>       SQLcl saved connection name (required)
  --workspace <name>        APEX workspace name (required)
  --minimal-id <id>         Override minimal application ID (9000-9099)
  --business-id <id>        Override business application ID (9000-9099)
  --apply                   Execute live import (default is dry-run)
  --confirm-ids <min,bus>   Required with --apply to confirm exact IDs
EOF
  exit 1
}

conn=""
workspace=""
minimal_id=""
business_id=""
apply=0
confirm_ids=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --connection) conn="$2"; shift 2;;
    --workspace) workspace="$2"; shift 2;;
    --minimal-id) minimal_id="$2"; shift 2;;
    --business-id) business_id="$2"; shift 2;;
    --apply) apply=1; shift;;
    --confirm-ids) confirm_ids="$2"; shift 2;;
    -h|--help) usage;;
    *) echo "Unknown option: $1" >&2; exit 1;;
  esac
done

if [[ -z "$conn" || -z "$workspace" ]]; then
  echo "Error: --connection and --workspace are required" >&2
  exit 1
fi

validate_range() {
  local id="$1"
  if [[ ! "$id" =~ ^[0-9]+$ ]] || [[ "$id" -lt 9000 || "$id" -gt 9099 ]]; then
    echo "Error: Application ID $id is outside allowed 9000-9099 range" >&2
    exit 1
  fi
}

if [[ -n "$minimal_id" ]]; then validate_range "$minimal_id"; fi
if [[ -n "$business_id" ]]; then validate_range "$business_id"; fi

if [[ -n "$minimal_id" && -n "$business_id" && "$minimal_id" == "$business_id" ]]; then
  echo "Error: --minimal-id and --business-id cannot be identical" >&2
  exit 1
fi

# Query occupied application IDs in 9000-9099 range
query_occupied=$(sql -S -name "$conn" <<'SQL'
set heading off feedback off pagesize 0 linesize 200 verify off
/* CONSUMER_OCCUPIED_QUERY */
select application_id || '|' || alias
  from apex_applications
 where application_id between 9000 and 9099;
exit
SQL
)

declare -A existing_ids
while IFS='|' read -r o_id o_alias; do
  o_id=$(echo "${o_id:-}" | tr -d '[:space:]')
  if [[ -n "$o_id" && "$o_id" =~ ^[0-9]+$ ]]; then
    existing_ids["$o_id"]=1
  fi
done <<< "$query_occupied"

# Check for collisions if IDs were explicitly provided
if [[ -n "$minimal_id" && -n "${existing_ids[$minimal_id]:-}" ]]; then
  echo "Error: Application ID collision: $minimal_id is already in use" >&2
  exit 1
fi
if [[ -n "$business_id" && -n "${existing_ids[$business_id]:-}" ]]; then
  echo "Error: Application ID collision: $business_id is already in use" >&2
  exit 1
fi

# Auto-propose IDs if not provided
if [[ -z "$minimal_id" ]]; then
  for ((cand=9000; cand<=9099; cand++)); do
    if [[ -z "${existing_ids[$cand]:-}" ]]; then
      minimal_id="$cand"
      existing_ids["$cand"]=1
      break
    fi
  done
fi

if [[ -z "$business_id" ]]; then
  for ((cand=9000; cand<=9099; cand++)); do
    if [[ -z "${existing_ids[$cand]:-}" ]]; then
      business_id="$cand"
      existing_ids["$cand"]=1
      break
    fi
  done
fi

if [[ -z "$minimal_id" || -z "$business_id" ]]; then
  echo "Error: Could not allocate two free application IDs in 9000-9099" >&2
  exit 1
fi

min_alias="TF-CONSUMER-MINIMAL-$minimal_id"
bus_alias="TF-CONSUMER-BUSINESS-$business_id"

if [[ $apply -eq 0 ]]; then
  cat <<EOF
PROVISIONING DRY RUN
Target Connection: $conn
Target Workspace:  $workspace
Minimal Consumer:  ID $minimal_id (Alias $min_alias)
Business Consumer: ID $business_id (Alias $bus_alias)

Proposed commands:
  apex import -input $ROOT/tests/live/consumer-apps/minimal -workspace $workspace -id $minimal_id -alias $min_alias -name "Theme Factory Minimal Consumer"
  apex import -input $ROOT/tests/live/consumer-apps/business -workspace $workspace -id $business_id -alias $bus_alias -name "Theme Factory Business Consumer"

(Re-run with --apply --confirm-ids $minimal_id,$business_id to execute)
EOF
  exit 0
fi

expected_conf="$minimal_id,$business_id"
if [[ "$confirm_ids" != "$expected_conf" ]]; then
  echo "Error: Confirmation mismatch: expected --confirm-ids $expected_conf, got '$confirm_ids'" >&2
  exit 1
fi

# Execute live provisioning
sql -S -name "$conn" <<SQL
whenever sqlerror exit failure
apex validate -input $ROOT/tests/live/consumer-apps/minimal -workspace $workspace
apex validate -input $ROOT/tests/live/consumer-apps/business -workspace $workspace
apex import -input $ROOT/tests/live/consumer-apps/minimal -workspace $workspace -id $minimal_id -alias $min_alias -name "Theme Factory Minimal Consumer"
apex import -input $ROOT/tests/live/consumer-apps/business -workspace $workspace -id $business_id -alias $bus_alias -name "Theme Factory Business Consumer"
exit
SQL

echo "PROVISIONING status=PASS minimal_id=$minimal_id business_id=$business_id"
