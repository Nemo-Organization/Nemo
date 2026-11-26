#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if [[ ! -x .venv/bin/python ]]; then
    echo "Install dependencies once with: uv sync --locked" >&2
    exit 1
fi

if [[ ! -f .env ]]; then
    cp .env.example .env
fi

exec .venv/bin/python -m app
