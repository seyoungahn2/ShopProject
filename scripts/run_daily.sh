#!/usr/bin/env bash
# 일일 글로벌 경제 보고서 생성 스크립트 (cron/systemd용)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

if [ -d .venv ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

exec global-econ run "$@"
