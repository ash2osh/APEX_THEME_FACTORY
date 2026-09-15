#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: cleanup-consumer-fixtures.sh --connection <conn> --workspace <ws> --minimal-id <id> --business-id <id> [options]

Options:
  --connection <name>            SQLcl saved connection name (required)
  --workspace <name>             APEX workspace name (required)
  --minimal-id <id>              Minimal consumer application ID (9000-9099, required)
  --business-id <id>             Business consumer application ID (9000-9099, required)
  --apply                        Execute live removal (default is dry-run)
  --confirm-aliases <min,bus>    Required with --apply to confirm exact aliases
EOF
  exit 1
}

conn=""
workspace=""
minimal_id=""
business_id=""
apply=0
confirm_aliases=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --connection) conn="$2"; shift 2;;
    --workspace) workspace="$2"; shift 2;;
    --minimal-id) minimal_id="$2"; shift 2;;
    --business-id) business_id="$2"; shift 2;;
    --apply) apply=1; shift;;
    --confirm-aliases) confirm_aliases="$2"; shift 2;;
    -h|--help) usage;;
    *) echo "Unknown option: $1" >&2; exit 1;;
  esac
done

if [[ -z "$conn" || -z "$workspace" || -z "$minimal_id" || -z "$business_id" ]]; then
  echo "Error: --connection, --workspace, --minimal-id, and --business-id are all required" >&2
  exit 1
fi

validate_range() {
  local id="$1"
  if [[ ! "$id" =~ ^[0-9]+$ ]] || [[ "$id" -lt 9000 || "$id" -gt 9099 ]]; then
    echo "Error: Application ID $id is outside allowed 9000-9099 range" >&2
    exit 1
  fi
}

validate_range "$minimal_id"
validate_range "$business_id"

expected_min_alias="TF-CONSUMER-MINIMAL-$minimal_id"
expected_bus_alias="TF-CONSUMER-BUSINESS-$business_id"

# Query existing apps
query_existing=$(sql -S -name "$conn" <<SQL
set heading off feedback off pagesize 0 linesize 200 verify off
/* CONSUMER_EXISTING_QUERY */
select application_id || '|' || alias
  from apex_applications
 where application_id in ($minimal_id, $business_id);
exit
SQL
)

declare -A found_aliases
while IFS='|' read -r a_id a_alias; do
  a_id=$(echo "${a_id:-}" | tr -d '[:space:]')
  a_alias=$(echo "${a_alias:-}" | tr -d '[:space:]')
  if [[ -n "$a_id" ]]; then
    found_aliases["$a_id"]="$a_alias"
  fi
done <<< "$query_existing"

# Verify aliases
if [[ -n "${found_aliases[$minimal_id]:-}" && "${found_aliases[$minimal_id]}" != "$expected_min_alias" ]]; then
  echo "Error: Alias mismatch for application $minimal_id: expected $expected_min_alias, found ${found_aliases[$minimal_id]}" >&2
  exit 1
fi

if [[ -n "${found_aliases[$business_id]:-}" && "${found_aliases[$business_id]}" != "$expected_bus_alias" ]]; then
  echo "Error: Alias mismatch for application $business_id: expected $expected_bus_alias, found ${found_aliases[$business_id]}" >&2
  exit 1
fi

if [[ $apply -eq 0 ]]; then
  cat <<EOF
CLEANUP DRY RUN
Targets:
  - Minimal Consumer:  ID $minimal_id (Alias $expected_min_alias)
  - Business Consumer: ID $business_id (Alias $expected_bus_alias)
Workspace: $workspace

Proposed cleanup block:
begin
    apex_application_install.set_workspace('$workspace');
    apex_application_install.set_keep_sessions(false);
    apex_application_install.remove_application($minimal_id);
    apex_application_install.remove_application($business_id);
end;
/

(Re-run with --apply --confirm-aliases $expected_min_alias,$expected_bus_alias to execute)
EOF
  exit 0
fi

expected_conf="$expected_min_alias,$expected_bus_alias"
if [[ "$confirm_aliases" != "$expected_conf" ]]; then
  echo "Error: Confirmation mismatch: expected --confirm-aliases $expected_conf, got '$confirm_aliases'" >&2
  exit 1
fi

# Execute cleanup
out=$(sql -S -name "$conn" <<SQL
whenever sqlerror exit failure
begin
    apex_application_install.set_workspace('$workspace');
    apex_application_install.set_keep_sessions(false);
    apex_application_install.remove_application($minimal_id);
    apex_application_install.remove_application($business_id);
end;
/
select count(*) from apex_applications where application_id in ($minimal_id, $business_id);
exit
SQL
)

echo "CLEANUP status=PASS minimal_id=$minimal_id business_id=$business_id"
