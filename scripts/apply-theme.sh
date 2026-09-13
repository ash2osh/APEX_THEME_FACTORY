#!/usr/bin/env bash
# Make sample-themes/<name> the DEFAULT theme: sets the fallback in the page-0 "theme" region and applies
# the theme's declarative template options (theme.json) to application.apx. All themes stay loaded;
# a visitor can still switch with ?theme=<name> (stored in localStorage) or ?theme=default.
# Follow with scripts/sync-static.sh and scripts/apex-import.sh.
set -euo pipefail
source "$(dirname "$0")/_env.sh"
name="${1:?usage: apply-theme.sh <theme-name>  (see sample-themes/)}"
json="$ROOT/sample-themes/$name/theme.json"
[[ -f "$json" ]] || { echo "no such theme: $json" >&2; exit 1; }
python3 - "$ROOT" "$name" "$json" <<'PY'
import json,re,sys
root,name,jp=sys.argv[1:4]; th=json.load(open(jp))
p=f"{root}/applications/ut/pages/p00000-global-page.apx"; s=open(p).read()
s2,n=re.subn(r"var DEFAULT = '[a-z0-9-]*';", f"var DEFAULT = '{name}';", s)
assert n==1, "page-0 theme region not found"; open(p,'w').write(s2)
nav=th.get("templateOptions",{}).get("navigationMenu",{}).get("style")
if nav:
    p=f"{root}/applications/ut/application.apx"; s=open(p).read()
    s2,n=re.subn(r"(\n            )t-TreeNav--(styleA|styleB|classic)\n", rf"\1{nav}\n", s)
    assert n==1, "navigationMenu style option not found"; open(p,'w').write(s2)
print(f"apply-theme: default={name} nav={nav}")
PY
