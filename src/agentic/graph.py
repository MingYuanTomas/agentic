"""规划 → Send 并行执行 → 汇总 → 有界审核修订。"""

from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from agentic.backend import Backend
from agentic.state import Plan, Review, WorkerState, WorkflowState


def initial_state(goal: str, max_revisions: int = 2) -> WorkflowState:
    """创建一次编排的初始状态，并在入口处校验输入边界。"""

    if not goal.strip():
        raise ValueError("任务目标不能为空。")
    if not 0 <= max_revisions <= 5:
        raise ValueError("max_revisions 必须在 0 到 5 之间。")
    return {
        "goal": goal.strip(),
        "results": [],
        "draft": "",
        "revisions": 0,
        "max_revisions": max_revisions,
    }

#传入变量类型Backend
def build_graph(backend: Backend):
    """组装 LangGraph：每个内部函数是一个节点，条件边负责并发分发和审核路由。"""

    def planner(state: WorkflowState):
        """规划节点：把目标写入 tasks，供下一步并行分发。"""

        # Plan.model_validate 相当于把模型的输出再检查一遍，确保 tasks 结构正确。
        plan = Plan.model_validate(backend.plan(state["goal"]))
        return {"tasks": plan.tasks}

    def dispatch(state: WorkflowState):
        """把每个子任务包装成一个 Send，让 worker 节点并行执行多份。"""

        # enumerate 同时给出下标和元素；下标之后用于恢复任务顺序。
        return [
            Send("worker", {"goal": state["goal"], "task": task, "index": index})
            for index, task in enumerate(state["tasks"])
        ]

    def worker(state: WorkerState):
        """执行节点：完成单个子任务，返回一份 WorkerResult。"""

        content = backend.work(state["goal"], state["task"])
        # 空结果是异常情况，提前报错，避免交付一份不完整的报告。
        if not content.strip():
            raise ValueError("子任务返回了空内容。")
        # 返回单元素列表，reducer 会把所有并行结果追加到全局 results。
        return {
            "results": [
                {
                    "index": state["index"],
                    "title": state["task"].title,
                    "content": content,
                }
            ]
        }

    def writer(state: WorkflowState):
        """汇总节点：按原始索引合并结果，必要时根据审核意见修订旧稿。"""

        # 第一次进入时还没有 review 和 draft，所以用 get 提供默认值。
        review = state.get("review")
        draft = state.get("draft", "")
        content = backend.write(
            state["goal"],
            # Send 并发返回的顺序不稳定，先按 index 恢复规划时的顺序。
            sorted(state["results"], key=lambda r: r["index"]),
            draft,
            review.feedback if review else "",
        )
        if not content.strip():
            raise ValueError("汇总智能体返回了空内容。")
        # 有旧稿说明这是一次修订；revisions 只在真正重写时增加。
        return {"draft": content, "revisions": state.get("revisions", 0) + bool(draft)}

    def reviewer(state: WorkflowState):
        """审核节点：写入是否通过及具体意见，供条件边决定去向。"""

        return {"review": Review.model_validate(backend.review(state["goal"], state["draft"]))}

    def route_review(state: WorkflowState) -> Literal["writer", "finish"]:
        """审核后的条件路由：未通过且还有修订额度则返回汇总，否则交付。"""

        if state["review"].approved or state["revisions"] >= state.get("max_revisions", 2):
            return "finish"
        return "writer"

    def finish(state: WorkflowState):
        """收尾节点：把审核结论转成稳定的最终状态。"""

        return {"status": "approved" if state["review"].approved else "revision_limit"}

    graph = StateGraph(WorkflowState)
    # 注册节点；节点函数只返回增量，LangGraph 负责合并回全局状态。
    graph.add_node("planner", planner)
    graph.add_node("worker", worker)
    graph.add_node("writer", writer)
    graph.add_node("reviewer", reviewer)
    graph.add_node("finish", finish)
    # 固定边：前一个节点结束后，无条件进入下一个节点。
    graph.add_edge(START, "planner")
    # 条件边：planner 之后调用 dispatch，按返回值决定去向（这里统一去 worker）。
    graph.add_conditional_edges("planner", dispatch, ["worker"])
    graph.add_edge("worker", "writer")
    graph.add_edge("writer", "reviewer")
    # 条件边：审核后由 route_review 决定回到 writer 还是进入 finish。
    graph.add_conditional_edges("reviewer", route_review)
    graph.add_edge("finish", END)
    # compile 把上面的描述编译成真正可执行的图。
    return graph.compile()
