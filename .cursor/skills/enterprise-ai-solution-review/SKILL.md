---
name: enterprise-ai-solution-review
description: Review AI solutions, AI product proposals, automation plans, enterprise transformation roadmaps, or vendor pitches from multiple executive and operating stakeholder perspectives. Use this skill whenever the user asks whether an AI方案/solution is valuable, feasible, investable, governable, or suitable for an enterprise customer.
---

# Enterprise AI Solution Review

Use this skill to review enterprise AI proposals from multiple roles, so the recommendation is commercially realistic, operationally useful, technically feasible, and governable. It is adapted from mature public agent skill patterns: explicit contract, input gathering, role-specific review lenses, evidence requirements, red flags, and a verdict.

## Contract

**Inputs:**
- AI product, solution, proposal, roadmap, architecture, pitch deck, or implementation plan
- Target enterprise, industry, users, workflow, and business problem
- Available data, integrations, cost assumptions, compliance needs, and success metrics

**Outputs:**
- Executive verdict: proceed, revise, pilot only, or reject
- Multi-role review from CEO, CFO, COO, CIO/IT, legal/risk, operations, and production/process management
- Risk register with mitigations
- Pilot design with measurable exit criteria
- Evidence gaps and next questions

**Success criteria:**
- Business value is separated from AI novelty
- Each stakeholder lens has concrete concerns and required evidence
- The recommendation includes a practical pilot or a clear reason not to proceed
- Missing data, ownership, compliance, or integration blockers are explicit

## Review setup

Collect or infer the following before reviewing:

- Target enterprise type, business unit, geography, and regulatory context.
- Current pain points, baseline process, and decision owner.
- Proposed AI capability, users, workflow, data sources, integrations, and operating model.
- Expected benefits, costs, implementation dependencies, risks, and success metrics.
- Deployment model: internal tool, customer-facing product, workflow automation, decision support, or autonomous agent.

If key information is missing, proceed with explicit assumptions and mark the highest-risk gaps. Do not invent financial or operational certainty.

## Review workflow

1. Clarify the use case and decision being made.
2. Identify the non-AI baseline: current manual process, rules-based automation, BI dashboard, RPA, search, or workflow redesign.
3. Map data and integration dependencies.
4. Review each stakeholder lens below.
5. Score readiness:
   - Value: high / medium / low
   - Feasibility: high / medium / low
   - Risk: high / medium / low
   - Adoption: high / medium / low
6. Recommend proceed, revise, pilot only, or reject.

## Role-based review lenses

### CEO

- Does this support strategy, differentiation, growth, resilience, or speed?
- Is the use case important enough to justify executive attention?
- What changes in market positioning, customer experience, or operating model?
- What should be piloted first to prove strategic value?

### CFO

- What is the ROI logic, payback path, and cash impact?
- Which costs are one-time vs recurring: licenses, compute, data labeling, integration, change management, compliance, maintenance?
- What financial assumptions are fragile?
- What metric proves value: revenue uplift, margin, cycle-time reduction, loss reduction, working capital, headcount leverage, or risk reduction?

### COO

- Does the proposal fit daily operations, ownership, escalation, and service levels?
- Which process steps change, and where can the AI fail safely?
- What training, SOP updates, and handoff rules are required?
- Does it reduce bottlenecks or create a new review queue?

### CIO / IT

- Can the solution integrate with existing systems, identity, permissions, logs, monitoring, and data architecture?
- Are build-vs-buy, vendor lock-in, model hosting, latency, and reliability clear?
- Are security, privacy, access control, backup, audit, and incident response addressed?
- What is needed for production support?

### Legal / Compliance / Risk

- What regulated decisions, sensitive data, explainability needs, retention rules, or audit obligations apply?
- Is there a human-in-the-loop process for high-impact decisions?
- Are model limitations, approval records, vendor terms, and data usage rights documented?
- What could create liability or reputational risk?

### Operations / Frontline Users

- Does the tool make the user faster or add reporting work?
- Are inputs available at the moment of work?
- Are recommendations understandable, editable, and easy to override?
- What incentives or habits may block adoption?

### Production / Plant / Process Management

- Does the solution respect physical constraints, quality systems, maintenance windows, batch records, deviations, and safety rules?
- Are real-time vs batch decisions separated clearly?
- Are alarms, overrides, and exception handling practical?
- How will the AI interact with MES, ERP, LIMS, QMS, SCADA, or planning systems when relevant?

## Cross-functional red flags

- No named business owner or operating owner.
- Benefits depend on perfect user adoption.
- Data is unavailable, untrusted, unstructured, or not permissioned for the proposed use.
- The AI is asked to make high-impact decisions without human review, appeal, audit, or rollback.
- Integration is described as "later" even though workflow value depends on it.
- Costs omit implementation, change management, monitoring, compliance, security, and maintenance.
- The proposal has no simpler baseline comparison.

## Output template

Use this structure:

```markdown
## Executive Verdict
Proceed / Revise / Pilot only / Reject

## Best Value Case
- [3 to 5 bullets]

## Readiness Score
| Dimension | Rating | Evidence |
|---|---|---|
| Value | High/Medium/Low | |
| Feasibility | High/Medium/Low | |
| Risk | High/Medium/Low | |
| Adoption | High/Medium/Low | |

## Stakeholder Review
| Role | Main Concern | Required Evidence | Recommendation |
|---|---|---|---|
| CEO | | | |
| CFO | | | |
| COO | | | |
| CIO / IT | | | |
| Legal / Risk | | | |
| Operations | | | |
| Production / Process | | | |

## Biggest Risks and Mitigations
- Risk:
  - Mitigation:

## Pilot Design
- Scope:
- Users:
- Data needed:
- Integrations:
- Metrics:
- Exit criteria:

## Governance
- Owner:
- Human review:
- Monitoring:
- Audit trail:
- Rollback:
```

## Quality bar

- Separate business value from AI novelty.
- Identify the non-AI baseline or simpler automation alternative.
- Make assumptions explicit.
- Prefer measurable pilots over broad transformation claims.
- Flag missing data, integration, or operating ownership as blockers when they would prevent production use.
