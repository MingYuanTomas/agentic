"""共享状态与模型结构化输出。

这里定义两类对象：

- Pydantic 模型：用于规划和审核的结构化输出，由 LangChain 的 function calling 生成。
- TypedDict：描述 LangGraph 节点之间流转的状态形状，不参与运行时校验。
"""

import operator
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field


class Task(BaseModel):
    """规划智能体拆出的一个子任务。"""

    title: str = Field(min_length=1, description="子任务标题")
    instruction: str = Field(min_length=1, description="子任务的具体执行要求")


class Plan(BaseModel):
    """规划结果：1 到 5 个可并行执行的子任务。"""

    tasks: list[Task] = Field(min_length=1, max_length=5, description="1 到 5 个独立子任务")


class Review(BaseModel):
    """审核结果：是否通过，以及对应的理由或修改意见。"""

    approved: bool = Field(description="是否达到用户要求，可直接交付")
    feedback: str = Field(min_length=1, description="通过理由或具体修改意见")


class WorkerResult(TypedDict):
    """单个 worker 的产出，最终被合并进 results 列表。"""

    index: int
    title: str
    content: str


class WorkflowState(TypedDict, total=False):
    """LangGraph 全局共享状态，节点通过返回值合并增量更新。"""

    # 用户原始任务目标，全程不变。
    goal: str
    # 规划节点写出的子任务列表，供下一步并行分发。
    tasks: list[Task]
    # 并行 worker 各自返回一段列表；operator.add 会把它们追加成一个列表，
    # 而不是后一个结果覆盖前一个。
    results: Annotated[list[WorkerResult], operator.add]
    # 汇总节点写出的 Markdown 报告，也是最终输出内容。
    draft: str
    # 审核节点写出的结论和意见。
    review: Review
    # 已经修订过几次；达到 max_revisions 后强制进入交付。
    revisions: int
    # 最多允许修订几次，由用户通过命令行参数控制。
    max_revisions: int
    # 只有 finish 节点会写入 status，用于决定 CLI 退出码。
    status: Literal["approved", "revision_limit"]


class WorkerState(TypedDict):
    """dispatch() 为每个并行 worker 单独构造的局部输入。"""

    goal: str
    task: Task
    index: int
