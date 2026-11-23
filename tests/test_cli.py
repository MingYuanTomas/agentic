"""覆盖 CLI 参数、环境变量读取和退出码。"""

import json

import pytest
from fakes import FakeBackend

from agentic.cli import main


def test_cli_writes_report_and_json(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr("agentic.cli.DeepSeekBackend", lambda **kwargs: FakeBackend())
    report = tmp_path / "nested" / "report.md"
    code = main(["run", "设计客服助手", "--json", "--output", str(report)])
    state = json.loads(capsys.readouterr().out)
    assert code == 0
    assert state["status"] == "approved"
    assert state["review"]["approved"] is True
    assert report.read_text(encoding="utf-8").strip() == state["draft"]


def test_revision_limit_has_distinct_exit_code(monkeypatch, capsys):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr("agentic.cli.DeepSeekBackend", lambda **kwargs: FakeBackend())
    assert main(["run", "设计助手", "--max-revisions", "0"]) == 2
    assert "revision_limit" in capsys.readouterr().err


def test_llm_missing_config_is_actionable(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert main(["run", "测试"]) == 1
    assert "DEEPSEEK_API_KEY" in capsys.readouterr().err


def test_deepseek_cli_reads_project_env(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    for key in (
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_MODEL",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_TIMEOUT",
    ):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text(
        "DEEPSEEK_API_KEY=test-key\nDEEPSEEK_MODEL=custom-deepseek\n"
        "DEEPSEEK_BASE_URL=https://model.invalid/v1\nDEEPSEEK_TIMEOUT=180\n",
        encoding="utf-8",
    )
    captured = {}

    def create_backend(**kwargs):
        captured.update(kwargs)
        return FakeBackend()

    monkeypatch.setattr("agentic.cli.DeepSeekBackend", create_backend)
    # 配置了名称和地址后不会用到类上的默认常量。
    assert main(["run", "读取 DeepSeek 配置"]) == 0
    assert captured == {
        "api_key": "test-key",
        "model": "custom-deepseek",
        "base_url": "https://model.invalid/v1",
        "timeout": 180,
    }
    capsys.readouterr()


@pytest.mark.parametrize("timeout", ["0", "-1", "invalid", "nan", "inf"])
def test_invalid_deepseek_timeout_is_actionable(monkeypatch, tmp_path, capsys, timeout):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_TIMEOUT", timeout)
    assert main(["run", "测试"]) == 1
    assert "DEEPSEEK_TIMEOUT 必须是正数" in capsys.readouterr().err


def test_graph_does_not_require_model_configuration(capsys):
    assert main(["graph"]) == 0
    assert "planner" in capsys.readouterr().out
