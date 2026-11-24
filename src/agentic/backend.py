"""将编排逻辑与模型实现隔离。

graph.py 只依赖 Backend 协议，不关心具体模型。这样测试可以注入本地实现，
生产可以替换成其他兼容 Chat Completions 的服务或带工具的子图。
"""

import json
from typing import Protocol

from agentic.state import Plan, Review, Task, WorkerResult


class Backend(Protocol):
    """编排层需要的四个能力；任何实现都必须在同一对象上提供全部方法。

    Protocol 本身不写实现，只约定“方法长什么样”。这样 graph.py 不依赖具体模型，
    测试可以用本地假实现，生产用 DeepSeek，互不影响。
    """

    def plan(self, goal: str) -> Plan:
        """把用户目标拆成 1 到 5 个独立子任务。"""
        ...

    def work(self, goal: str, task: Task) -> str:
        """完成单个子任务并返回文本结果。"""
        ...

    def write(self, goal: str, results: list[WorkerResult], draft: str, feedback: str) -> str:
        """把子任务结果（及旧稿、审核意见）整合成 Markdown 报告。"""
        ...

    def review(self, goal: str, draft: str) -> Review:
        """审核报告并返回是否通过及具体反馈。"""
        ...


class LLMBackend:
    """使用支持结构化输出的 Chat Completions 兼容模型。"""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout: float = 120,
        extra_body: dict | None = None,
    ):
        # 把第三方库的导入放在 __init__ 里，只有真正创建模型时才加载它。
        from langchain_openai import ChatOpenAI

        # ChatOpenAI 兼容 DeepSeek 等 OpenAI 风格接口；use_responses_api=False
        # 强制走 Chat Completions 协议，确保 function calling 行为一致。
        # self用于全局变量
        self.model = ChatOpenAI(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout=timeout,
            max_retries=2,
            extra_body=extra_body,
            use_responses_api=False,
        )
        # 规划和审核需要稳定的 JSON，所以绑定结构化输出；其余角色只返回文本。
        self.planner = self.model.with_structured_output(Plan, method="function_calling")
        self.reviewer = self.model.with_structured_output(Review, method="function_calling")

    def plan(self, goal: str) -> Plan:
        # with_structured_output 会通过 tool_calls 返回 Plan；这里再做一次校验兜底。
        # 消息用元组列表表示，("system", ...) 是系统提示词，("human", ...) 是用户输入。
        result = self.planner.invoke(
            [
                (
                    "system",
                    "你是任务规划智能体。将目标拆为 1 到 5 个可独立并行完成的子任务，覆盖交付要求。",
                ),
                ("human", goal),
            ]
        )
        return Plan.model_validate(result)

    def _text(self, system: str, payload: dict) -> str:
        from langchain_core.output_parsers import StrOutputParser

        # 非结构化角色统一走“系统提示词 + JSON 化的任务数据”文本通道。
        # self.model | StrOutputParser() 表示“先问模型，再把输出转成纯字符串”。
        result = (self.model | StrOutputParser()).invoke(
            [
                ("system", system),
                ("human", json.dumps(payload, ensure_ascii=False)),
            ]
        )
        if not result.strip():
            raise ValueError("模型返回了空文本，请检查模型配置。")
        return result

    def work(self, goal: str, task: Task) -> str:
        return self._text(
            "你是执行智能体。完成给定子任务，用中文给出具体结果。你没有联网、文件或代码执行工具；不得声称已检索或执行。标注需要验证的假设。",
            {"goal": goal, "task": task.model_dump()},
        )

    def write(self, goal: str, results: list[WorkerResult], draft: str, feedback: str) -> str:
        return self._text(
            "你是汇总智能体。围绕用户目标整合子任务结果，输出可直接交付的中文 Markdown。如有旧稿和审核意见，逐项修订。不得编造验证结果。",
            {"goal": goal, "results": results, "previous_draft": draft, "feedback": feedback},
        )

    def review(self, goal: str, draft: str) -> Review:
        result = self.reviewer.invoke(
            [
                (
                    "system",
                    "你是审核智能体。检查交付内容是否覆盖目标、具体可用、无明显自相矛盾。未通过时给出具体可执行的修改意见。",
                ),
                ("human", json.dumps({"goal": goal, "draft": draft}, ensure_ascii=False)),
            ]
        )
        return Review.model_validate(result)


# 继承LLMBackend
class DeepSeekBackend(LLMBackend):
    """DeepSeek 官方 Chat Completions 接口，使用非思考模式支持指定工具输出。"""

    DEFAULT_MODEL = "deepseek-flash"
    DEFAULT_BASE_URL = "https://api.deepseek.com"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 120,
    ):
        # super().__init__ 调用父类 LLMBackend 的构造方法，避免重复写模型初始化代码。
        # DeepSeek 思考模式不支持 named tool_choice；规划和审核依赖它，
        # 因此所有请求都关闭 thinking，换取稳定的结构化输出。
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout=timeout,
            # DeepSeek 的思考模式不支持结构化输出所用的 named tool_choice。
            extra_body={"thinking": {"type": "disabled"}},
        )
