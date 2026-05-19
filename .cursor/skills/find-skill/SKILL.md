---
name: find-skill
description: Discover, choose, and apply the most relevant project or personal skills before planning or editing. Use this skill whenever a task is broad, multi-domain, involves testing, app development, AI evaluation, enterprise analysis, or the user asks which skill to use.
---

# Find Skill

Use this skill to avoid missing useful project instructions. It helps the agent discover available skills, decide which ones apply, and follow them during the task. It is adapted from mature public skill patterns: frontmatter-driven discovery, token-efficient loading, explicit selection rules, and trigger-focused descriptions.

## Contract

**Inputs:**
- User task
- Repository skill directories
- Optional global user skill directories

**Outputs:**
- Short list of relevant skills
- Reason each skill applies
- Execution plan that follows the selected skills

**Success criteria:**
- Relevant skills are found before deep planning or editing
- Skills are selected by description and task fit, not name alone
- Conflicts are resolved in favor of direct user instructions and project-level guidance

## When to use

- At the beginning of a new task when the repo may contain task-specific skills.
- Before testing, deployment, evaluation, enterprise analysis, or app development work.
- When the user asks whether a skill exists or wants to add new skills.
- When a task spans multiple domains and may require more than one skill.
- When a task is important enough that missing a workflow would cause rework.

## Discovery steps

1. Check project-level skill locations:
   - `.cursor/skills/*/SKILL.md`
   - `.agents/skills/*/SKILL.md`
2. Check user-level skill locations when accessible:
   - `~/.cursor/skills/*/SKILL.md`
   - `~/.agents/skills/*/SKILL.md`
3. Read the frontmatter for each candidate skill:
   - `name`
   - `description`
   - optional `paths`
4. Choose skills whose descriptions directly match the current task.
5. If multiple skills apply, use the narrowest skill for the task-specific workflow and the broader skill for general quality checks.

## Skill map for this repo

- `fair-ai-evaluation`: use for model evals, benchmarks, train/test splits, leakage, backtests, and anti-cheating review.
- `app-development-expert`: use for app features, bugs, UI, API, database, auth, testing, and production readiness.
- `enterprise-ai-solution-review`: use for enterprise AI proposals and stakeholder review from CEO, CFO, COO, CIO/IT, legal/risk, operations, and production roles.
- `industry-ai-solution-review`: use with enterprise review for CDMO, pharma manufacturing, biotech operations, financial investment, asset management, private equity, and investment research contexts.
- `find-skill`: use first when the right skill is unclear.

## Selection rules

- Do not use a skill only because the name sounds related; the description must fit the current task.
- Prefer project-level skills over user-level skills when they conflict.
- Follow direct user instructions and repository rules before skill suggestions.
- If no skill applies, proceed normally and mention only if the user asks.
- Use more than one skill when the task naturally spans domains, for example app development plus fair evaluation, or enterprise review plus CDMO/financial industry review.

## Invocation patterns

Cursor can trigger skills automatically from the `description`. The user can also call them explicitly:

- `/fair-ai-evaluation`
- `@fair-ai-evaluation`
- "Please use the fair-ai-evaluation skill..."
- "First use find-skill, then decide which skills apply."

If explicit slash or mention syntax is unavailable in the current interface, read the named skill file and follow it manually.

## Suggested response pattern

- State which skill or skills are relevant.
- Briefly say why they apply.
- Apply the workflow directly; do not only summarize the skill.

Example:

```markdown
Relevant skills:
- `find-skill`: selected available project workflows.
- `enterprise-ai-solution-review`: the task is an enterprise AI proposal review.
- `industry-ai-solution-review`: the customer is a CDMO.

I will use those workflows and return a stakeholder review with industry red flags.
```

## Maintenance checklist

- Each skill directory name must match the `name` field.
- Each skill needs a clear `description` that says when to use it.
- Keep skills focused. Split a skill when it mixes unrelated workflows.
- Put long reference material in `references/` when the main `SKILL.md` becomes hard to scan.
- Make descriptions slightly explicit about trigger contexts so agents do not underuse the skill.
