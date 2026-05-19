---
name: app-development-expert
description: Build, debug, refactor, or review production-quality apps end to end. Use this skill whenever the task involves a feature, UI, API, database, auth, state, performance, accessibility, testing, release readiness, or a multi-file code change that should be handled like a senior app engineer.
---

# App Development Expert

Use this skill to approach app work like a senior product engineer: understand the product goal, make small durable changes, verify behavior end to end, and leave the codebase easier to maintain. It is adapted from mature public agent skill patterns: explicit contract, acceptance criteria first, phased build loop, browser/runtime verification, and judge-style review.

## Contract

**Inputs:**
- User request, bug report, product requirement, or review target
- Repository code, docs, tests, logs, and runtime behavior
- Existing architecture, conventions, and deployment constraints

**Outputs:**
- Working app behavior or actionable review
- Small scoped code changes that fit existing patterns
- Test evidence from the exact modified path
- Clear summary of risk, limitations, and next action

**Success criteria:**
- The user-facing behavior matches the request
- Existing contracts, data, auth, and security boundaries are preserved
- Tests or manual evidence prove the changed behavior runs
- No unrelated rewrites or avoidable dependency additions are introduced

## Phase 1: Understand and scope

1. Start from the user journey and failure mode, not just the first relevant file.
2. Read local patterns before adding abstractions, dependencies, state managers, routes, APIs, or test helpers.
3. Define acceptance criteria in observable terms:
   - User can perform a specific action
   - System responds correctly in success, loading, empty, error, and permission states
   - Regressions are covered by relevant tests
4. Identify constraints:
   - Data model and migrations
   - Authentication and authorization
   - External services and secrets
   - Browser, mobile, or accessibility requirements

## Phase 2: Design the smallest durable change

- Prefer the smallest implementation that satisfies the product need and fits existing architecture.
- Reuse existing components, hooks, utilities, schemas, services, and test helpers.
- Add an abstraction only when it removes real duplication or clarifies a stable boundary.
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

## Phase 3: Build loop

1. Make the narrow code change.
2. Run the most relevant static checks or unit tests early.
3. Exercise the exact feature path:
   - API: call the route/service with realistic inputs and error cases.
   - UI: open the real page, interact with the control, and inspect state changes.
   - Background job: run the job or a representative worker path.
4. If the test fails, diagnose from runtime evidence and loop back to the smallest failing layer.

## Testing expectations

- Define the success state before coding: what would convince a skeptical reviewer that the feature or fix works?
- Add or update automated tests when touching logic that already has tests or introducing new reusable behavior.
- Manually test UI changes in the real app when visual or interaction behavior changes.
- Verify the exact modified path runs, not only that the app starts or unrelated tests pass.
- When a bug is reproducible, show the failing behavior first when practical, then show the fixed behavior.

## Phase 4: Judge-style review

- Does the implementation solve the actual user-facing problem?
- Are edge states handled without hiding real errors?
- Are tests meaningful, deterministic, and close to the changed behavior?
- Is the naming clear and consistent with the codebase?
- Are logs useful without exposing secrets or noisy internals?
- Are there simpler existing utilities or patterns that should be reused?
- Did the change introduce avoidable scope creep?
- Could this fail for permissions, empty data, slow network, mobile layout, or repeated submission?

Use this verdict:

```markdown
## App Change Review
- Verdict: PASS / FAIL / PASS WITH NOTES
- Evidence:
- Remaining risk:
- Follow-up:
```

## Common red flags

- A feature only works with seeded happy-path data.
- UI has no loading, error, disabled, or empty state.
- API trusts client-side checks for authorization.
- New dependency solves a small problem already covered by local utilities.
- Test only proves the app starts, not that the modified path works.
- Change touches unrelated files without a product reason.

## Output style

- Explain changes in terms of product behavior and engineering tradeoffs.
- Call out test evidence clearly.
- Be honest about any untested risk or environment limitation.
