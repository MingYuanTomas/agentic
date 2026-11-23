"""测试专用固定后端，避免测试调用真实模型。"""

from agentic.state import Plan, Review, Task


class FakeBackend:
    """返回固定内容，模拟“初稿缺验收标准 → 修订一次 → 通过”的链路。"""

    def plan(self, goal: str) -> Plan:
        return Plan(
            tasks=[
                Task(title="需求分析", instruction="明确目标、输入输出和交付范围"),
                Task(title="实施方案", instruction="给出实现步骤和模块职责"),
                Task(title="验证方案", instruction="列出正常路径、异常路径和验收方式"),
            ]
        )

    def work(self, goal: str, task: Task) -> str:
        return f"围绕「{goal}」：{task.instruction}。先实现最小可运行版本，再逐步扩展。"

    def write(self, goal: str, results: list, draft: str, feedback: str) -> str:
        sections = "\n\n".join(f"## {r['title']}\n\n{r['content']}" for r in results)
        report = f"# {goal}\n\n> 测试固定响应。\n\n{sections}"
        if feedback:
            report += "\n\n## 验收标准\n\n- 全部子任务产出已合并。"
        return report

    def review(self, goal: str, draft: str) -> Review:
        approved = "## 验收标准" in draft
        return Review(
            approved=approved,
            feedback="已包含验收标准。" if approved else "请补充独立的验收标准章节。",
        )
