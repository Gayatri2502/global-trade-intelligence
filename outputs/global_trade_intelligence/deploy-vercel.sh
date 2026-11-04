#!/usr/bin/env bash
set -euo pipefail
source_dir=$(cd "$(dirname "$0")" && pwd)
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
mkdir "$stage/public" "$stage/api"
cp "$source_dir"/{style.css,app.js,feedback.mjs,login.mjs,metrics.mjs,world.geojson} "$stage/public/"
cp "$source_dir"/{index.html,server.py,ledger_client.py,bulk_contacts.py,vercel.json} "$stage/"
cp "$source_dir/api/private.py" "$stage/api/"
printf 'openpyxl==3.1.5\n' > "$stage/requirements.txt"
cd "$stage"
vercel link --yes --project trade-ledger --scope alphacentauricai-8714s-projects
vercel deploy --prod --yes --scope alphacentauricai-8714s-projects
