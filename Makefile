# OmniKB / agent orchestration Makefile
# Container CLI: override with make CONTAINER_CLI=docker ...

CONTAINER_CLI ?= podman
COMPOSE = $(CONTAINER_CLI) compose

.PHONY: check compose-up compose-down compose-ps research-qdrant-up research-qdrant-down bench agent-log digest

## Run all quality gates (mypy + ruff + pytest). Sub-agents must pass before opening PRs.
check:
	ruff check src tests
	ruff format --check src tests
	mypy src
	bandit -c pyproject.toml -r src
	pytest -x -q

## Start OmniKB stack (set DOCKER_HOST=npipe:////./pipe/podman-machine-default on Windows Podman).
compose-up:
	$(COMPOSE) up --build -d

compose-down:
	$(COMPOSE) down

compose-ps:
	$(COMPOSE) ps

## Start isolated research Qdrant on port 6334 (loopback; never use 6333 for experiments).
research-qdrant-up:
	$(CONTAINER_CLI) run -d --name qdrant-research \
	  -p 127.0.0.1:6334:6333 \
	  -v qdrant_research_data:/qdrant/storage \
	  qdrant/qdrant:latest
	@echo "Research Qdrant running on http://127.0.0.1:6334"

research-qdrant-down:
	$(CONTAINER_CLI) stop qdrant-research && $(CONTAINER_CLI) rm qdrant-research || true

## Run embedding benchmark suite (Research Agent). Requires research Qdrant up.
bench:
	QDRANT_URL=http://127.0.0.1:6334 python -m pytest docs/research/benchmarks/ -v --tb=short

agent-log:
	Get-Content AGENT_WORK_LOG.md -Wait 2>/dev/null || tail -f AGENT_WORK_LOG.md

digest:
	python -m omnikb.agents.haiku_utility digest
