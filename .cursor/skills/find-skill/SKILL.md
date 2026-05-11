---
name: find-skill
description: Use this skill at the start of a task to discover, choose, and apply the most relevant project or personal skills before planning or editing.
---

# Find Skill

Use this skill to avoid missing useful project instructions. It helps the agent discover available skills, decide which ones apply, and follow them during the task.

## When to use

- At the beginning of a new task when the repo may contain task-specific skills.
- Before testing, deployment, evaluation, enterprise analysis, or app development work.
- When the user asks whether a skill exists or wants to add new skills.
- When a task spans multiple domains and may require more than one skill.

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

## Selection rules

- Do not use a skill only because the name sounds related; the description must fit the current task.
- Prefer project-level skills over user-level skills when they conflict.
- Follow direct user instructions and repository rules before skill suggestions.
- If no skill applies, proceed normally and mention only if the user asks.

## Suggested response pattern

- State which skill or skills are relevant.
- Briefly say why they apply.
- Apply the workflow directly; do not only summarize the skill.

## Maintenance checklist

- Each skill directory name must match the `name` field.
- Each skill needs a clear `description` that says when to use it.
- Keep skills focused. Split a skill when it mixes unrelated workflows.
- Put long reference material in `references/` when the main `SKILL.md` becomes hard to scan.
