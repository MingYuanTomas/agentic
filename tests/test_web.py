"""覆盖 Web 服务的页面、任务轮询和报告下载。"""

import time

from fakes import FakeBackend
from fastapi.testclient import TestClient

import agentic.web as web


def test_web_service_runs_and_downloads_report(monkeypatch):
    monkeypatch.setattr(web, "_backend", lambda: FakeBackend())
    client = TestClient(web.app)

    assert client.get("/").status_code == 200
    assert "Agentic" in client.get("/").text

    response = client.post("/api/run", json={"goal": "测试Web服务", "max_revisions": 2})
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    task = {}
    for _ in range(200):
        task = client.get(f"/api/task/{task_id}").json()
        if task["status"] in {"done", "error"}:
            break
        time.sleep(0.01)

    assert task["status"] == "done"
    assert task["result_status"] == "approved"
    assert len(task["progress"]) > 0

    download = client.get(f"/api/task/{task_id}/download")
    assert download.status_code == 200
    assert "attachment" in download.headers["content-disposition"]
    assert download.text == task["draft"]


def test_web_service_rejects_blank_goal(monkeypatch):
    monkeypatch.setattr(web, "_backend", lambda: FakeBackend())
    client = TestClient(web.app)
    assert client.post("/api/run", json={"goal": "", "max_revisions": 2}).status_code == 422
