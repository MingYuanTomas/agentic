"""命令行入口：调用 DeepSeek 执行多智能体编排。"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

from agentic.backend import DeepSeekBackend
from agentic.graph import build_graph, initial_state

# 节点名称到中文描述的映射，仅用于终端进度提示。
NODE_LABELS = {
    "planner": "规划：拆分子任务",
    "worker": "并行执行：完成子任务",
    "writer": "汇总：生成报告",
    "reviewer": "审核：检查报告",
    "finish": "交付：写入最终状态",
}


def _json_default(value):
    """让 json.dumps 能序列化 Pydantic 模型（如 Review）。"""

    if isinstance(value, BaseModel):
        return value.model_dump()
    raise TypeError(f"无法序列化 {type(value).__name__}")


class _NoopBackend:
    """仅用于 ``graph`` 命令绘制图结构，不会被实际调用。"""

    def plan(self, goal):
        raise NotImplementedError

    def work(self, goal, task):
        raise NotImplementedError

    def write(self, goal, results, draft, feedback):
        raise NotImplementedError

    def review(self, goal, draft):
        raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """解析命令、组装后端并执行编排，返回供 shell 使用的退出码。"""

    # argparse 负责解析命令行参数；subparsers 支持 run 和 graph 两个子命令。
    parser = argparse.ArgumentParser(description="LangGraph 多智能体编排示例")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="执行任务")
    run.add_argument("goal", help="任务目标")
    run.add_argument("--max-revisions", type=int, default=2, help="最大修订次数（0 到 5）")
    run.add_argument("--output", type=Path, help="保存 Markdown 报告")
    run.add_argument("--json", action="store_true", help="输出完整 JSON 状态")
    commands.add_parser("graph", help="输出 Mermaid 流程图，无需密钥")
    args = parser.parse_args(argv)
    if args.command == "graph":
        # 输出 Mermaid 文本，不依赖密钥，适合直接查看图结构。
        # _NoopBackend 不会真的调用模型，只是满足 build_graph 的参数要求。
        print(build_graph(_NoopBackend()).get_graph().draw_mermaid())
        return 0

    try:
        # 默认从当前目录读取 .env；start.sh 会先切换到项目根目录。
        # load_dotenv 把 .env 里的 KEY=VALUE 变成当前进程的环境变量。
        load_dotenv(Path.cwd() / ".env")
        # 先校验任务目标并创建初始状态；这一步失败会直接返回 1。
        state = initial_state(args.goal, args.max_revisions)
        # 必须显式提供密钥；模型和地址有默认值，可被环境覆盖。
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise ValueError("请复制 .env.example 为 .env，并填写 DEEPSEEK_API_KEY。")
        try:
            timeout = float(os.getenv("DEEPSEEK_TIMEOUT", "120"))
        except ValueError:
            raise ValueError("DEEPSEEK_TIMEOUT 必须是正数，单位为秒。") from None
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("DEEPSEEK_TIMEOUT 必须是正数，单位为秒。")
        backend = DeepSeekBackend(
            api_key=api_key,
            model=os.getenv("DEEPSEEK_MODEL", "").strip() or DeepSeekBackend.DEFAULT_MODEL,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "").strip() or DeepSeekBackend.DEFAULT_BASE_URL,
            timeout=timeout,
        )

        graph = build_graph(backend)
        print("开始执行…", file=sys.stderr, flush=True)
        # 同时以 updates 和 values 两种模式读取执行过程：
        # updates 能看到每个节点完成，values 能得到合并后的完整状态。
        for mode, chunk in graph.stream(
            state, config={"recursion_limit": 30}, stream_mode=["updates", "values"]
        ):
            if mode == "values":
                state = chunk
            else:
                for node_name in chunk:
                    print(
                        f"已完成：{NODE_LABELS.get(node_name, node_name)}",
                        file=sys.stderr,
                        flush=True,
                    )
        if args.output:
            # mkdir(parents=True) 会自动创建不存在的父目录。
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(state["draft"] + "\n", encoding="utf-8")
        if args.json:
            print(json.dumps(state, default=_json_default, ensure_ascii=False, indent=2))
        else:
            # 报告走 stdout，诊断信息走 stderr，方便管道消费报告本身。
            print(state["draft"])
            print(f"\n状态：{state['status']}；修订次数：{state['revisions']}", file=sys.stderr)
            print(f"审核意见：{state['review'].feedback}", file=sys.stderr)
        return 0 if state["status"] == "approved" else 2
    except (ValueError, OSError) as exc:
        # 用户输入或本地配置问题：直接展示可读信息。
        print(f"运行失败：{exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        # 第三方 API 错误正文可能含敏感数据，只保留异常类型，不直接回显。
        # 这里不打印完整异常，避免把请求头或返回内容泄漏到终端。
        print(
            f"运行失败（{type(exc).__name__}）：请检查模型连接、权限与结构化输出支持。",
            file=sys.stderr,
        )
        return 1
