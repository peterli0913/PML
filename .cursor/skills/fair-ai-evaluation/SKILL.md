---
name: fair-ai-evaluation
description: Use this skill when designing or auditing AI, ML, analytics, or agent evaluation workflows that need standardized train/test splits, leakage prevention, reproducible metrics, and anti-cheating safeguards.
---

# Fair AI Evaluation

Use this skill to make model, agent, or software evaluation fair, reproducible, and resistant to accidental or intentional cheating.

## Core principles

- Keep training, validation, and test data separate before any modeling, prompt tuning, feature selection, or manual iteration.
- Treat the test set as a final exam. Do not inspect labels, tune prompts, tune thresholds, rewrite examples, or choose metrics based on test-set performance.
- Record every split, seed, dataset version, prompt version, model version, and evaluation command needed to reproduce results.
- Prefer pre-registered acceptance criteria: define metrics, minimum quality bars, and failure cases before running final tests.
- Report negative results and edge cases. Do not cherry-pick favorable runs.

## Standard train/validation/test flow

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

## Leakage and cheating checklist

- No duplicate or near-duplicate records cross split boundaries.
- No future information appears in training features for time-sensitive tasks.
- No labels, outcomes, reviewer notes, or post-event fields leak into inputs.
- No entity leakage: the same customer, company, drug program, asset, supplier, employee, or transaction chain is not split across train and test when that would inflate results.
- No prompt leakage: test labels, scoring rubrics with answer keys, or hidden examples are not included in prompts, tools, retrieval indexes, or memory.
- No benchmark overfitting: repeated submissions to the same test set are tracked and limited.
- No manual answer correction before scoring unless the same correction process is defined for production.

## Evidence to collect

- Dataset version and split manifest.
- Evaluation script or command.
- Metric definitions and confidence intervals when possible.
- Confusion matrix or per-category breakdown for classification tasks.
- Examples of false positives, false negatives, hallucinations, refusals, and boundary failures.
- A short statement of what was not tested.

## Final report structure

- Goal: what decision this evaluation supports.
- Data: source, version, split method, and exclusion criteria.
- Protocol: frozen prompts, models, tools, seeds, thresholds, and commands.
- Results: main metrics plus segment-level breakdowns.
- Integrity checks: leakage checks, duplicate checks, and anti-cheating controls.
- Decision: pass, fail, or inconclusive, with next action.
