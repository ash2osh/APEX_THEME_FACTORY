# Theme Workflow Benchmark

This benchmark compares the recipe-driven workflow with the preserved four-theme baseline. Token counts are supplied by the agent harness; they are never inferred from text size.

## Current result

| Measure | Target | Median / result | Status |
|---|---:|---:|---|
| Scaffold | < 10 s | UNMEASURED | UNVERIFIED |
| Cached theme check | < 30 s | UNMEASURED | UNVERIFIED |
| First app-102 preview | < 120 s | UNMEASURED | UNVERIFIED |
| Agent token reduction | >= 50% | UNMEASURED | UNVERIFIED |
| Overall | all targets | 0 candidate runs | UNVERIFIED |

## Repeatable protocol

Run exactly three trials in clean disposable worktrees, using the same requirement prompt:

1. A compact light theme with no custom font.
2. A dense technical dark theme with the complete dark-token treatment.
3. A bilingual Arabic/Latin theme with four pinned WOFF2 weights.

For each trial, stop timing after candidate-lane PASS. Record scaffold, cached check, candidate lane, and first-preview wall times; commands; files read and written; validation reruns; browser rows; and the harness-provided input/output token totals. Exclude only documented SQLcl/database outages. Do not change thresholds after observing results.

## Source binding

- Baseline source commit: `54375b86410346a0b7f6a50124090936df828bec`
- Baseline recipe SHA-256: `1ea2fbf9b393a5f7e09a25aca0609e29c5190f3b6a310046fa9cd5b3b69ffe0e`
- Baseline total tokens: UNMEASURED

No candidate run records were supplied. All targets remain `UNVERIFIED`.
