"""覆盖 LangGraph 并发、审核路由、修订上限和失败传播。"""

from threading import Barrier

import pytest
from fakes import FakeBackend
from pydantic import ValidationError

from agentic.graph import build_graph, initial_state
from agentic.state import Plan, Review


def test_parallel_workers_are_joined_and_review_feedback_is_applied():
    barrier = Barrier(3)

    class ParallelBackend(FakeBackend):
        def __init__(self):
            self.writer_inputs = []

        def work(self, goal, task):
            # 只有三个 worker 实际并发执行，这个 barrier 才能通过。
            barrier.wait(timeout=10)
            return super().work(goal, task)

        def write(self, goal, results, draft, feedback):
            self.writer_inputs.append((list(results), feedback))
            return super().write(goal, results, draft, feedback)

    backend = ParallelBackend()
    state = build_graph(backend).invoke(initial_state("搭建知识库助手"))
    assert state["status"] == "approved"
    assert state["revisions"] == 1
    assert len(state["results"]) == 3
    assert len(backend.writer_inputs) == 2
    for results, _ in backend.writer_inputs:
        assert [result["index"] for result in results] == [0, 1, 2]
    assert backend.writer_inputs[1][1] == "请补充独立的验收标准章节。"


@pytest.mark.parametrize("limit", [0, 2, 5])
def test_review_loop_stops_at_limit(limit):
    class RejectBackend(FakeBackend):
        def review(self, goal, draft):
            return Review(approved=False, feedback="需要修改。")

    state = build_graph(RejectBackend()).invoke(
        initial_state("测试审核上限", limit), config={"recursion_limit": 30}
    )
    assert state["status"] == "revision_limit"
    assert state["revisions"] == limit
    assert len(state["results"]) == 3


def test_approved_draft_finishes_without_revision():
    class ApproveBackend(FakeBackend):
        def review(self, goal, draft):
            return Review(approved=True, feedback="通过。")

    state = build_graph(ApproveBackend()).invoke(initial_state("测试直接通过"))
    assert state["revisions"] == 0
    assert state["status"] == "approved"


def test_worker_failure_propagates_instead_of_producing_partial_report():
    class BrokenBackend(FakeBackend):
        def work(self, goal, task):
            raise RuntimeError("worker failed")

    with pytest.raises(RuntimeError, match="worker failed"):
        build_graph(BrokenBackend()).invoke(initial_state("失败测试"))


def test_empty_plan_is_rejected():
    with pytest.raises(ValidationError):
        Plan(tasks=[])


@pytest.mark.parametrize("goal,limit", [("  ", 2), ("任务", -1), ("任务", 6)])
def test_invalid_inputs_are_rejected(goal, limit):
    with pytest.raises(ValueError):
        initial_state(goal, limit)
