---
name: industry-ai-solution-review
description: Review AI solutions for CDMO, pharmaceutical manufacturing, biotech operations, financial investment, asset management, private equity, family office, or investment research businesses. Use this skill with enterprise-ai-solution-review whenever the customer, data, workflow, or risks are CDMO/pharma or finance/investment specific.
---

# Industry AI Solution Review

Use this skill together with `enterprise-ai-solution-review` when the customer is a CDMO, life-science manufacturing organization, financial investment firm, fund, family office, asset manager, or private equity team. It is adapted from mature public agent skill patterns: domain selection, contract, red flags, evidence requirements, and output add-ons.

## Contract

**Inputs:**
- Enterprise AI proposal, product idea, automation plan, diligence memo, or operating roadmap
- Target industry: CDMO/life sciences manufacturing or financial investment
- Data sources, workflows, compliance constraints, users, and deployment model

**Outputs:**
- Industry-specific fit assessment
- Domain red flags and mitigations
- Data and integration readiness checklist
- Pilot use case and measurable exit criteria
- Evidence required before production rollout

**Success criteria:**
- Regulated workflows and sensitive data boundaries are respected
- Domain-specific systems, users, and operating constraints are named
- Backtest, quality, compliance, and audit risks are not hand-waved
- Recommendation is practical for the industry's actual workflow

## Use with enterprise review

1. First apply `enterprise-ai-solution-review` for executive and operating stakeholder lenses.
2. Then apply the relevant industry lens below.
3. If the customer spans both industries, review both and keep risks separate.
4. Add the "Review output add-on" sections to the enterprise review.

## CDMO and life-science manufacturing lens

Review whether the AI proposal respects:

- GMP, GxP, data integrity, audit trails, validation, and change control.
- Batch records, deviations, CAPA, OOS/OOT investigations, QA review, and release workflows.
- Tech transfer, scale-up, process development, analytical development, and manufacturing scheduling.
- LIMS, QMS, MES, ERP, ELN, historians, instrument data, and document management integrations.
- Client confidentiality, molecule/program segregation, IP protection, and project-level access control.
- Regulatory inspection readiness and explainability of AI-assisted decisions.

### High-value CDMO use cases

- Deviation triage and investigation support.
- Batch record review assistance.
- Tech-transfer document extraction and gap analysis.
- Capacity planning, campaign scheduling, and bottleneck prediction.
- Quality trend monitoring across assays, equipment, sites, and suppliers.
- Proposal/RFP response support with controlled knowledge retrieval.
- Knowledge assistant for SOPs, methods, validation packs, and client project history with strict access control.

### CDMO readiness checks

- Data integrity: source systems, audit trail, versioning, and ALCOA+ expectations.
- Validation: intended use, risk classification, qualification, and change-control plan.
- Human review: QA, production, engineering, or MSAT approval points.
- Segregation: client, molecule, program, and site-level permission boundaries.
- Integration: LIMS, QMS, MES, ERP, ELN, historian, DMS, and scheduling systems.
- Inspection readiness: traceable source documents and reproducible AI outputs.

### CDMO red flags

- AI directly making release, quality, safety, or compliance decisions without human approval.
- Training data mixes clients, projects, or molecules without access controls.
- No validation plan for regulated workflows.
- No audit trail for AI inputs, outputs, user actions, and source documents.
- Benefits depend on data that is not digitized, trusted, or accessible.
- Proposal assumes cross-client learning without clear consent, anonymization, or contractual basis.

## Financial investment lens

Review whether the AI proposal respects:

- MNPI controls, restricted lists, research compliance, surveillance, and record retention.
- Data licensing, alternative data rights, model explainability, and investment committee governance.
- Portfolio risk, factor exposure, liquidity, concentration, drawdown, and scenario analysis.
- Research workflow: sourcing, screening, diligence, memo drafting, monitoring, and exit analysis.
- Human accountability for investment decisions.

### High-value investment use cases

- Deal or public-equity screening with transparent scoring.
- Earnings call, filing, news, and expert-call synthesis with source citations.
- Portfolio company KPI monitoring and variance explanation.
- Investment memo drafting with assumption tracking.
- Risk alerts from market, credit, operational, and regulatory signals.
- Fundraising and LP reporting automation with controlled data access.
- Private-market diligence assistant for CIMs, financials, QoE reports, customer calls, and management presentations.

### Financial readiness checks

- Data timing: every feature and document was available at the decision timestamp.
- Data rights: licenses allow model, retrieval, and internal redistribution use.
- Compliance: MNPI, restricted lists, marketing rules, retention, and surveillance.
- Explainability: investment committee can trace claims to sources and assumptions.
- Portfolio risk: exposure, liquidity, concentration, drawdown, factor, and scenario views.
- Workflow: analyst, PM, IC, compliance, and operations handoffs are explicit.

### Financial red flags

- Backtests without walk-forward testing, transaction costs, slippage, or survivorship-bias controls.
- Model trained or evaluated on data that would not have been available at decision time.
- No source traceability for claims in investment memos.
- AI output presented as advice without compliance review.
- Vendor or data usage terms conflict with investment workflows.
- Model output cannot explain why a security, deal, or portfolio action was recommended.

## Review output add-on

Add these sections to the enterprise review:

- Industry fit: why the solution matters in this sector.
- Regulatory and compliance constraints.
- Data readiness and integration gaps.
- Domain-specific pilot use case.
- Domain-specific red flags and mitigations.
- Evidence needed before production rollout.

## Pilot examples

### CDMO pilot

- Scope: one site, one workflow, one product family or client-approved data boundary.
- Users: QA reviewer, production supervisor, MSAT/process engineer, project manager.
- Metrics: review cycle time, deviation aging, right-first-time rate, rework, audit-trail completeness, user override rate.
- Exit criteria: measurable process improvement plus QA-approved validation and audit evidence.

### Financial investment pilot

- Scope: one strategy, one research workflow, or one portfolio monitoring process.
- Users: analyst, PM, compliance reviewer, operations stakeholder.
- Metrics: research cycle time, source coverage, citation accuracy, false alert rate, IC memo quality, compliance exceptions.
- Exit criteria: better decision support than baseline without MNPI, licensing, or audit issues.
