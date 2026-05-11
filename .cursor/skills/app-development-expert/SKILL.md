---
name: app-development-expert
description: Use this skill when building, refactoring, debugging, or reviewing an application end to end, especially when product quality, maintainability, security, testing, and release readiness matter.
---

# App Development Expert

Use this skill to approach app work like a senior product engineer: understand the product goal, make small durable changes, verify behavior end to end, and leave the codebase easier to maintain.

## Working approach

- Start from the user journey and the failure mode, not just the file that appears relevant.
- Read local patterns before adding abstractions, dependencies, state managers, routes, APIs, or test helpers.
- Keep changes scoped. Prefer the smallest implementation that satisfies the product need and fits existing architecture.
- Preserve public contracts, persisted data formats, migrations, API compatibility, and security boundaries.
- Avoid broad rewrites unless the request is explicitly about architecture or the existing design blocks correctness.

## Implementation checklist

- Data model: validate types, nullability, ownership, permissions, and migration needs.
- API/backend: check authentication, authorization, validation, idempotency, error shape, observability, and rollback behavior.
- Frontend: check loading, empty, error, disabled, success, and optimistic-update states.
- State: avoid duplicated derived state; keep cache invalidation explicit.
- Performance: identify expensive loops, network waterfalls, large renders, unbounded queries, and missing pagination.
- Security: avoid leaking secrets, PII, internal IDs, unsafe HTML, insecure redirects, or overly broad permissions.
- Accessibility: use semantic elements, labels, keyboard flow, focus states, and readable contrast.

## Testing expectations

- Define the success state before coding: what would convince a skeptical reviewer that the feature or fix works?
- Add or update automated tests when touching logic that already has tests or introducing new reusable behavior.
- Manually test UI changes in the real app when visual or interaction behavior changes.
- Verify the exact modified path runs, not only that the app starts or unrelated tests pass.
- When a bug is reproducible, show the failing behavior first when practical, then show the fixed behavior.

## Review checklist

- Does the implementation solve the actual user-facing problem?
- Are edge states handled without hiding real errors?
- Are tests meaningful, deterministic, and close to the changed behavior?
- Is the naming clear and consistent with the codebase?
- Are logs useful without exposing secrets or noisy internals?
- Are there simpler existing utilities or patterns that should be reused?

## Output style

- Explain changes in terms of product behavior and engineering tradeoffs.
- Call out test evidence clearly.
- Be honest about any untested risk or environment limitation.
