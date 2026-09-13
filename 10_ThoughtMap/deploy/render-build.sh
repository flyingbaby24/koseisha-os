#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
node --version
python --version
npm --prefix threejs ci --include=dev
VITE_THOUGHTMAP_API_BASE_URL=/ npm --prefix threejs run build
test -s threejs/dist/index.html
cd web
python -m pip install -r requirements-api.txt
python -m alembic -c alembic.ini upgrade head
