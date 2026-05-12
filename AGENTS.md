# AGENTS.md

## Cursor Cloud specific instructions

This repository ("PML") is currently a **document-only repository** with no runnable source code, applications, or services. It contains:

- `README.md` — a stub README
- Several Chinese-language business/proposal documents (`.pdf`, `.docx`) related to industrial predictive maintenance systems

### Development environment

- **No dependencies** to install (no `package.json`, `requirements.txt`, `pyproject.toml`, etc.).
- **No lint, test, or build commands** are available.
- **No services** to start or run.

If source code is added in the future, update this file with the appropriate setup instructions, lint/test/build commands, and service startup notes.

### Global skills

Five global skills are installed at `~/.cursor/skills/` so that all repos' Cloud Agents can discover them automatically. They originate from this repo's `.cursor/skills/` directory (branch `cursor/add-agent-skills-2ba1`, or `main` after merge).

| Skill | When to use |
|---|---|
| `find-skill` | First skill to consult when unsure which skill applies |
| `fair-ai-evaluation` | Model evals, benchmarks, train/test splits, leakage, backtests |
| `app-development-expert` | App features, bugs, UI, API, database, auth, testing |
| `enterprise-ai-solution-review` | Enterprise AI proposals from multi-stakeholder perspectives |
| `industry-ai-solution-review` | CDMO/pharma or finance/investment industry-specific review |

The update script syncs these skills from the repo on every VM startup. If skills are added or changed in the repo, they will be picked up automatically.
