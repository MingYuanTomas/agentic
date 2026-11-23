.PHONY: install run test lint graph

GOAL ?= 设计一个企业知识库问答助手

install:
	.venv/bin/python -m pip install -e '.[dev]'

run:
	./start.sh run "$(GOAL)"

test:
	.venv/bin/python -m pytest -q

lint:
	.venv/bin/ruff check .

graph:
	.venv/bin/agentic graph
