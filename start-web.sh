#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [[ ! -x "$PROJECT_DIR/.venv/bin/uvicorn" ]]; then
    echo "未找到 uvicorn，请先按 docs/启动与项目介绍.md 安装依赖。" >&2
    exit 1
fi

exec "$PROJECT_DIR/.venv/bin/uvicorn" agentic.web:app --host 127.0.0.1 --port "${PORT:-8000}"
