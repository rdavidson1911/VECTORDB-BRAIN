# Orchestrator session reports

After each multi-agent cycle, the Orchestrator writes:

`ORCHESTRATION_SESSION_REPORT-YYYY-MM-DD.md`

## Template

```markdown
# Orchestration session report — YYYY-MM-DD

## Executive summary

## Results by agent

| Agent | Status | Artifacts / commits | Gates |

## Recommendations

1. (priority order)

## Questions driving next steps

1. ...

## Worktree teardown record

- Removed: ...
- Branches deleted: ...
- `git worktree list` after: ...

## Appendix — new AGENT_WORK_LOG entries

(paste session log lines)
```

Teardown SOP: [scripts/Invoke-AgentWorktreeTeardown.ps1](../../scripts/Invoke-AgentWorktreeTeardown.ps1)
