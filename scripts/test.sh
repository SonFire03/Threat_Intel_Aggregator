#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT_DIR"

if [ "${USE_DOCKER:-0}" = "1" ]; then
  exec docker compose run --rm iocvault pytest "$@"
fi

exec python -m pytest "$@"
