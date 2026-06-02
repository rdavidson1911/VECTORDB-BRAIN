# ──────────────────────────────────────────────────
# AGENT ORCHESTRATION TARGETS
# Added by setup-agent-orchestration.ps1
# ──────────────────────────────────────────────────

.PHONY: check research-qdrant-up research-qdrant-down bench agent-log digest

## Run all quality gates (mypy + ruff + pytest). Sub-agents must pass before opening PRs.
check:
	ruff check .
	mypy --strict omnikb/
	pytest -x -q

## Start isolated research Qdrant on port 6334 (safe for agent experiments).
research-qdrant-up:
	docker run -d --name qdrant-research \
	  -p 6334:6333 \
	  -v qdrant_research_data:/qdrant/storage \
	  qdrant/qdrant:latest
	@echo "Research Qdrant running on http://localhost:6334"

## Stop and remove the research Qdrant container.
research-qdrant-down:
	docker stop qdrant-research && docker rm qdrant-research || true

## Run embedding benchmark suite (Research Agent). Requires research Qdrant up.
bench:
	QDRANT_URL=http://localhost:6334 python -m pytest docs/research/benchmarks/ -v --tb=short

## Tail the agent work log.
agent-log:
	Get-Content AGENT_WORK_LOG.md -Wait 2>/dev/null || tail -f AGENT_WORK_LOG.md

## Generate today's Haiku digest.
digest:
	python -m omnikb.agents.haiku_utility digest
