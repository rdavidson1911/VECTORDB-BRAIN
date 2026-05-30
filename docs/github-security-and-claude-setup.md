# GitHub security and Claude Code setup

This guide covers repository security for **rdavidson1911/VECTORDB-BRAIN** and how to use **Claude Code** for review, analysis, and testing. Claude is **not** added as a human “collaborator” seat; it runs via the **Claude GitHub App** and **GitHub Actions** with scoped permissions.

## 1. Branch history (important)

Remote `main` currently has only GitHub’s **Initial commit**. The feature branch `feat/web-console-and-curation-gate` was pushed from a **separate history**, so GitHub **cannot open a normal PR** until histories are linked.

Pick one approach:

### Option A — Replace empty `main` with your line of development (typical for a new public repo)

```powershell
cd I:\VECTORDB-BRAIN
git fetch origin
# Backup remote main if needed: git branch backup-main origin/main
git push origin feat/web-console-and-curation-gate:main --force-with-lease
```

Then set default branch to `main` in **Settings → General** if it isn’t already.

### Option B — Merge unrelated histories (keeps both commits)

```powershell
git fetch origin
git checkout -b integrate-main origin/main
git merge origin/feat/web-console-and-curation-gate --allow-unrelated-histories -m "merge: integrate OmniKB feature branch"
git push origin integrate-main:main
```

After either option, open a PR from new feature branches against `main` as usual.

## 2. Security checklist (repository settings)

Do these in **GitHub → Settings** (repo admin required).

| Control | Where | Recommendation |
|--------|--------|----------------|
| Default branch | General | `main` after Option A or B |
| Branch protection | Branches → Add rule for `main` | Require PR, require status checks (`python`, `web`), no force-push |
| Secret scanning | Code security | Enable (public repos: available) |
| Dependabot alerts | Code security | Enable (see API below) |
| Dependabot security updates | Code security | Enable |
| Private vulnerability reporting | Security → Policy | Use `SECURITY.md` (already in repo) |

### Enable alerts via CLI (optional)

```powershell
gh api -X PUT repos/rdavidson1911/VECTORDB-BRAIN/vulnerability-alerts
gh api -X PUT repos/rdavidson1911/VECTORDB-BRAIN/automated-security-fixes
```

Dependabot version PRs are configured in `.github/dependabot.yml`.

## 3. CI quality gates (already in repo)

Workflow: `.github/workflows/ci.yml` — runs on PRs and pushes to `main` / `master`:

- Python: ruff, mypy, bandit, pytest
- Web: eslint, production build

After `main` is fixed, every PR gets these checks. Optionally require them in branch protection.

## 4. Claude Code — review, analysis, testing

### What “contributor” means here

- **Not supported:** inviting `@claude` as a person in **Settings → Collaborators** (there is no Claude user seat).
- **Supported:** install the **[Claude GitHub App](https://github.com/apps/claude)** on this repository and add **`ANTHROPIC_API_KEY`** as a repository secret. Workflow: `.github/workflows/claude-code.yml`.

### Setup steps

1. **Install the app** (repo admin): https://github.com/apps/claude
   Permissions: Contents, Issues, Pull requests (read/write) — required for PR comments and fixes.

2. **API key secret:** **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `ANTHROPIC_API_KEY`
   - Value: from https://console.anthropic.com/ (or your org key policy).

3. **Quick install from Claude Code CLI (optional):** in terminal, run `/install-github-app` inside Claude Code.

4. **Push workflow** (this repo includes `.github/workflows/claude-code.yml`).

5. **Use on a PR or issue:** comment e.g.
   `@claude review this PR for security issues, path safety, and curation gate bypasses. Run tests and summarize findings.`

Claude will read `CLAUDE.md`, run allowed tools per action config, and can read CI results when `actions: read` is granted.

### Automatic review on every PR (optional)

Anthropic also documents **GitHub Code Review** (automatic comments without `@claude`). Configure from Claude Code docs after the app is installed. Keep human review via `.github/CODEOWNERS` for `@rdavidson1911`.

### Local review (Cursor / Claude Desktop)

Same standards as CI:

```powershell
python -m ruff check src tests
python -m mypy src
python -m bandit -c pyproject.toml -r src
python -m pytest
cd web; npm run lint; npm run build
```

## 5. Operator security reminders

- Never commit `.env` or API keys.
- Curation gate on `data/sources/curated/` must stay enabled on `main` (`CURATION_ALLOW_OVERRIDE=false`).
- See `docs/security-hardening-guide.md` and `CLAUDE.md` §4.

## 6. References

- [Claude Code GitHub Actions](https://docs.anthropic.com/en/docs/claude-code/github-actions)
- [Claude GitHub App](https://github.com/apps/claude)
- Repository `SECURITY.md`
