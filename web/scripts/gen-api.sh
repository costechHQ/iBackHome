#!/bin/sh
# Regenerates the typed API client from the backend's OpenAPI document. Run from web/: `bun run gen:api`.
# Needs uv (backend) and bun (web). No database is needed: FastAPI builds the document from the code.
# CI (.github/workflows/api-contract.yml) runs this and fails if the committed files differ.
set -eu

web_dir=$(cd "$(dirname "$0")/.." && pwd)
out_dir="$web_dir/src/common/api"

(
  cd "$web_dir/../backend"
  uv run --quiet python - "$out_dir/openapi.json" <<'PY'
import json
import sys

from app.main import app

with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as f:
    json.dump(app.openapi(), f, indent=2, ensure_ascii=False)
    f.write("\n")
PY
)

cd "$web_dir"
bun x openapi-typescript src/common/api/openapi.json --output src/common/api/schema.d.ts
