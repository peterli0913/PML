---
name: fair-ai-evaluation
description: Design or audit fair AI, ML, analytics, benchmark, or agent evaluations. Use this skill whenever a task mentions train/test splits, validation, benchmarks, backtests, evals, data leakage, prompt leakage, cherry-picking, anti-cheating, or claims that a model/system is "better" and needs trustworthy proof.
---

# Fair AI Evaluation

Use this skill to make evaluation fair, reproducible, and resistant to accidental or intentional cheating. It is adapted from mature public skill patterns: explicit contracts, acceptance criteria first, leakage checks, evidence capture, and a final judge-style verdict.

## Contract

**Inputs:**
- Task or hypothesis being evaluated
- Dataset, benchmark, logs, prompts, product workflow, or backtest
- Candidate systems, models, prompts, agents, or software versions
- Business or product decision that depends on the result

**Outputs:**
- Evaluation protocol with split strategy and leakage controls
- Reproducible run plan with metrics and commands
- Integrity checklist covering contamination and cheating risks
- Final verdict: PASS, FAIL, or INCONCLUSIVE

**Success criteria:**
- Train, validation, and test boundaries are explicit
- Test-set use is limited and documented
- Metrics match the real decision being made
- Leakage and cherry-picking risks are checked before claims are accepted

## Decision tree

1. **Is this a shipped product behavior test?**
   - Use product acceptance criteria and end-to-end testing.
   - Still use this skill if model quality, benchmark claims, or train/test fairness are involved.
2. **Is this ML, LLM, ranking, forecasting, backtesting, or agent evaluation?**
   - Use the full protocol below.
3. **Is the user asking for a quick comparison?**
   - Create a lightweight validation protocol first.
   - Do not call it a final test unless the held-out test process is followed.

## Core principles

- Split before iteration. Keep train, validation, and test data separate before modeling, prompt tuning, feature selection, retrieval tuning, threshold tuning, or manual example curation.
- Treat the test set as a final exam. Do not inspect labels, tune prompts, tune thresholds, rewrite examples, or choose metrics based on test-set performance.
- Record split method, seed, dataset version, retrieval corpus version, prompt version, model version, tool version, and command used for every run.
- Define metrics and minimum quality bars before final testing.
- Report negative results, uncertainty, and edge cases. Do not cherry-pick favorable runs.

## Standard protocol

1. Define the task, target users, business goal, and expected failure modes.
2. Freeze the raw dataset version and document source, time range, filters, and exclusions.
3. Split data into train, validation, and test sets using a method that matches deployment reality:
   - Time-based split for forecasting, finance, operations, sales, and production data.
   - Group-based split when the same customer, project, molecule, asset, plant, or account can appear multiple times.
   - Stratified split when class imbalance matters.
4. Use the train set for fitting and prompt/example design.
5. Use the validation set for model selection, threshold tuning, prompt iteration, and feature decisions.
6. Use the test set once for final evaluation after decisions are frozen.
7. If the test result drives more iteration, create a new held-out test set or label it clearly as validation-style iteration.

## Leakage and cheating checks

- No duplicate or near-duplicate records cross split boundaries.
- No future information appears in training features for time-sensitive tasks.
- No labels, outcomes, reviewer notes, or post-event fields leak into inputs.
- No entity leakage: the same customer, company, drug program, asset, supplier, employee, or transaction chain is not split across train and test when that would inflate results.
- No prompt leakage: test labels, scoring rubrics with answer keys, or hidden examples are not included in prompts, tools, retrieval indexes, or memory.
- No benchmark overfitting: repeated submissions to the same test set are tracked and limited.
- No manual answer correction before scoring unless the same correction process is defined for production.
- No retrieval leakage: test answers, answer keys, confidential grading notes, or post-hoc summaries are not available to RAG indexes, memory, tools, or caches.
- No backtest leakage: financial or operational features are available only as of the decision timestamp; include transaction costs, latency, slippage, survivorship bias, and realistic execution constraints when relevant.
- No evaluator leakage: the judge model, rubric, or human reviewer does not receive hidden labels unless the scoring step requires them.

## Metric selection

- Classification: precision, recall, F1, ROC/PR curves, calibration, and confusion matrix by segment.
- Ranking/retrieval: recall@k, precision@k, MRR/NDCG, source coverage, and citation correctness.
- Generation: factuality, completeness, refusal quality, harmful hallucination rate, citation support, and human review rubric.
- Forecasting/backtesting: walk-forward validation, drawdown, hit rate, calibration, benchmark baseline, and costs.
- Operations: cycle time, throughput, rework, escalation rate, user override rate, and incident rate.

Always compare against a baseline: current manual process, simple heuristic, previous model, or non-AI automation.

## Evidence to collect

- Dataset version and split manifest.
- Evaluation script or command.
- Metric definitions and confidence intervals when possible.
- Confusion matrix or per-category breakdown for classification tasks.
- Examples of false positives, false negatives, hallucinations, refusals, and boundary failures.
- Logs or artifacts proving the exact evaluated path ran.
- A short statement of what was not tested.

## Report template

Use this structure:

```markdown
## Evaluation Verdict
PASS / FAIL / INCONCLUSIVE

## Decision Supported
[What decision this evaluation is meant to support]

## Protocol
- Dataset/source:
- Split method:
- Frozen versions:
- Baseline:
- Metrics:
- Commands or run steps:

## Results
- Main result:
- Segment breakdown:
- Failure examples:
- Confidence/uncertainty:

## Integrity Checks
- Leakage checks:
- Anti-cheating controls:
- Known limitations:

## Next Action
[Ship, revise, expand validation, collect more data, or reject claim]
```
