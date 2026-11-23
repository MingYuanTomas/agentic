"""通过本地 HTTP mock 验证真实模型适配器，不发送外部请求。"""

import json

import httpx
import langchain_openai
import pytest

from agentic.backend import DeepSeekBackend, LLMBackend
from agentic.graph import build_graph, initial_state


@pytest.mark.parametrize("backend_type", [LLMBackend, DeepSeekBackend])
def test_llm_graph_parses_function_calls_and_text(monkeypatch, backend_type):
    requests = []

    def handle(request):
        payload = json.loads(request.content)
        if backend_type is DeepSeekBackend:
            assert str(request.url) == "https://api.deepseek.com/chat/completions"
            assert payload["model"] == "deepseek-flash"
            assert payload["thinking"] == {"type": "disabled"}
            assert request.headers["authorization"] == "Bearer test-key"
        requests.append(payload)
        message = {"role": "assistant", "content": "这是执行或汇总的模型文本。"}
        reason = "stop"
        if payload.get("tools"):
            name = payload["tools"][0]["function"]["name"]
            assert payload["tool_choice"] == {"type": "function", "function": {"name": name}}
            assert payload["tools"][0]["function"].get("strict") is not True
            arguments = (
                {
                    "tasks": [
                        {"title": "设计", "instruction": "设计模块"},
                        {"title": "验证", "instruction": "定义验收标准"},
                    ]
                }
                if name == "Plan"
                else {"approved": True, "feedback": "覆盖要求。"}
            )
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_test",
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(arguments)},
                    }
                ],
            }
            reason = "tool_calls"
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": "test-model",
                "choices": [{"index": 0, "message": message, "finish_reason": reason}],
            },
        )

    original = langchain_openai.ChatOpenAI
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:

        def create_model(**kwargs):
            return original(**kwargs, http_client=client)

        monkeypatch.setattr(langchain_openai, "ChatOpenAI", create_model)
        if backend_type is DeepSeekBackend:
            backend = backend_type(api_key="test-key")
        else:
            backend = backend_type(
                api_key="test-key", model="test-model", base_url="https://model.invalid/v1"
            )
        result = build_graph(backend).invoke(initial_state("设计助手"))

    assert result["status"] == "approved"
    assert len(result["results"]) == 2
    assert result["draft"] == "这是执行或汇总的模型文本。"
    assert len(requests) == 5
