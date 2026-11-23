#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [[ ! -x "$PROJECT_DIR/.venv/bin/python" ]]; then
    echo "未找到项目虚拟环境，请先按 docs/启动与项目介绍.md 的安装步骤创建 .venv。" >&2
    exit 1
fi

if [[ $# -eq 0 ]]; then
    set -- --help
fi

exec "$PROJECT_DIR/.venv/bin/python" -m agentic "$@"
