"""FastAPI Web 服务：接收任务目标，后台执行编排，并提供报告下载。"""

import math
import os
import threading
import uuid
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from agentic.backend import DeepSeekBackend
from agentic.graph import build_graph, initial_state

# 项目根目录；确保无论从哪里启动 uvicorn，都能读到项目根目录的 .env。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

UI_PATH = Path(__file__).with_name("web_ui.html")

# 与 CLI 保持一致的中文进度标签。
NODE_LABELS = {
    "planner": "规划：拆分子任务",
    "worker": "并行执行：完成子任务",
    "writer": "汇总：生成报告",
    "reviewer": "审核：检查报告",
    "finish": "交付：写入最终状态",
}


class RunRequest(BaseModel):
    goal: str = Field(min_length=1, description="任务目标")
    max_revisions: int = Field(default=2, ge=0, le=5, description="最大修订次数")


# 单机内存任务表：进程重启后任务会丢失，适合本地演示。
_TASKS: dict[str, dict] = {}
_LOCK = threading.Lock()


def _backend() -> DeepSeekBackend:
    """按环境变量创建 DeepSeek 后端，配置缺失时抛出可读错误。"""

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ValueError("缺少 DEEPSEEK_API_KEY，请在项目根目录的 .env 中配置。")
    try:
        timeout = float(os.getenv("DEEPSEEK_TIMEOUT", "120"))
    except ValueError:
        raise ValueError("DEEPSEEK_TIMEOUT 必须是正数，单位为秒。") from None
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("DEEPSEEK_TIMEOUT 必须是正数，单位为秒。")
    return DeepSeekBackend(
        api_key=api_key,
        model=os.getenv("DEEPSEEK_MODEL", "").strip() or DeepSeekBackend.DEFAULT_MODEL,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "").strip() or DeepSeekBackend.DEFAULT_BASE_URL,
        timeout=timeout,
    )


def _run_task(task_id: str, goal: str, max_revisions: int) -> None:
    """在后台线程执行编排，并持续更新任务进度。"""

    with _LOCK:
        _TASKS[task_id] = {
            "status": "running",
            "progress": [],
            "draft": "",
            "review": "",
            "revisions": 0,
            "result_status": "",
            "error": None,
        }

    try:
        backend = _backend()
        graph = build_graph(backend)
        state = initial_state(goal, max_revisions)
        for mode, chunk in graph.stream(
            state, config={"recursion_limit": 30}, stream_mode=["updates", "values"]
        ):
            if mode == "values":
                state = chunk
            else:
                for node_name in chunk:
                    with _LOCK:
                        _TASKS[task_id]["progress"].append(NODE_LABELS.get(node_name, node_name))

        with _LOCK:
            _TASKS[task_id].update(
                {
                    "status": "done",
                    "draft": state["draft"],
                    "review": state["review"].feedback,
                    "revisions": state["revisions"],
                    "result_status": state["status"],
                }
            )
    except Exception as exc:  # noqa: BLE001 - 任务失败信息需要返回给前端。
        with _LOCK:
            _TASKS[task_id]["status"] = "error"
            _TASKS[task_id]["error"] = str(exc)


app = FastAPI(title="Agentic 编排服务", version="0.1.0")


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """返回提问与下载页面。"""

    return HTMLResponse(UI_PATH.read_text(encoding="utf-8"))


@app.post("/api/run")
def create_run(payload: RunRequest) -> dict:
    """创建一次后台任务并返回任务 ID。"""

    task_id = uuid.uuid4().hex
    thread = threading.Thread(
        target=_run_task,
        args=(task_id, payload.goal.strip(), payload.max_revisions),
        daemon=True,
    )
    thread.start()
    return {"task_id": task_id}


@app.get("/api/task/{task_id}")
def get_task(task_id: str) -> dict:
    """返回任务状态、进度和最终报告。"""

    with _LOCK:
        task = _TASKS.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        return {
            "task_id": task_id,
            "status": task["status"],
            "progress": list(task["progress"]),
            "draft": task["draft"],
            "review": task["review"],
            "revisions": task["revisions"],
            "result_status": task["result_status"],
            "error": task["error"],
        }


@app.get("/api/task/{task_id}/download")
def download_report(task_id: str) -> Response:
    """以附件形式下载最终 Markdown 报告。"""

    with _LOCK:
        task = _TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task["status"] != "done":
        raise HTTPException(status_code=409, detail="任务尚未完成")

    filename = "agentic-report.md"
    quoted = quote(filename)
    return Response(
        content=task["draft"],
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quoted}"
        },
    )
