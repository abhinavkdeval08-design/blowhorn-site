#!/usr/bin/env bash
# Point a worker's wrangler.json at the shared signups D1 database.
# Usage: resolve-d1.sh <worker-dir>
#
# The database_id committed in wrangler.json is a placeholder: the real id
# only exists once the database is created in Cloudflare, which this script
# does (wrangler d1 create) if `wrangler d1 list` does not already show it.
# The script is quiet by design: the caller's repository logs are public,
# so it prints one line and nothing that names account resources.
set -euo pipefail
dir="${1:?usage: resolve-d1.sh <worker-dir>}"
: "${CLOUDFLARE_API_TOKEN:?}" "${CLOUDFLARE_ACCOUNT_ID:?}"
WRANGLER_VERSION="${WRANGLER_VERSION:-4.151.3}"
name="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["d1_databases"][0]["database_name"])' "$dir/wrangler.json")"
log="$(mktemp)"
trap 'rm -f "$log"' EXIT
export WRANGLER_SEND_METRICS=false CI=true
fail_log() {
  # Print wrangler's own error lines, with long identifiers redacted: the
  # caller's repository logs are public.
  grep -iE 'error|failed|unknown argument|invalid' "$log" | sed -E 's/[0-9a-f]{32}/<id>/g; s/[A-Za-z0-9_-]{40}/<token>/g' | head -10 >&2 || true
}
(cd "$dir" && npx --yes "wrangler@$WRANGLER_VERSION" d1 list --json >"$log" 2>&1) ||
  { echo "resolve-d1: d1 list failed" >&2; fail_log; exit 1; }
id="$(python3 - "$log" "$name" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
want = sys.argv[2]
dbs = data if isinstance(data, list) else data.get("d1_databases", [data])
for db in dbs:
    if isinstance(db, dict) and db.get("name") == want and db.get("uuid"):
        print(db["uuid"])
        break
PY
)"
if [ -z "$id" ]; then
  # d1 create takes no --json flag in this wrangler version, so the id is
  # read back from a second list call instead of from create's output.
  (cd "$dir" && npx --yes "wrangler@$WRANGLER_VERSION" d1 create "$name" >"$log" 2>&1) ||
    { echo "resolve-d1: d1 create failed" >&2; fail_log; exit 1; }
  (cd "$dir" && npx --yes "wrangler@$WRANGLER_VERSION" d1 list --json >"$log" 2>&1) ||
    { echo "resolve-d1: d1 list failed" >&2; fail_log; exit 1; }
  id="$(python3 - "$log" "$name" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
want = sys.argv[2]
dbs = data if isinstance(data, list) else data.get("d1_databases", [data])
for db in dbs:
    if isinstance(db, dict) and db.get("name") == want and db.get("uuid"):
        print(db["uuid"])
        break
PY
)"
fi
[ -n "$id" ] || { echo "resolve-d1: no database id found" >&2; exit 1; }
python3 - "$dir/wrangler.json" "$id" <<'PY'
import json, sys
path, new_id = sys.argv[1], sys.argv[2]
doc = json.load(open(path))
doc["d1_databases"][0]["database_id"] = new_id
with open(path, "w") as f:
    json.dump(doc, f, indent=2)
    f.write("\n")
PY
echo "resolve-d1: database ready"
