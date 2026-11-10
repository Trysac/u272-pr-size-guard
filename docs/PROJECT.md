# Project record

## Objective

Measure pull request size from git numstat or unified diffs, ignore lock and generated files, flag warn and fail thresholds, and suggest how to split the change into reviewable slices.

## Scope

In scope:

- `parse_numstat` and `parse_unified_diff` for `git diff --numstat` and unified diff text.
- Reviewable line counting: `FileChange.lines = added + deleted`; binary files contribute 0.
- The two ignore-pattern forms and `DEFAULT_IGNORE` (lock files, minified files, snapshots, `vendor/**`, `dist/**`, `node_modules/**`, `__snapshots__/**`).
- `assess` with `warn`/`fail` thresholds and `counted`/`ignored`/`files` results.
- `suggest_slices` grouping by directory depth with first-fit decreasing packing and oversized slices.
- `PrSizeError` with codes `parse_error`, `input_too_large`, `invalid_pattern`, and `invalid_options`.
- The CLI in `src/pr_size_guard/__main__.py`.

Out of scope:

- Calling git or the GitHub API.
- Commenting on pull requests or applying labels.
- Semantic grouping of tests with sources.
- Runtime dependencies; the library uses only the Python standard library.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | 691672 / 65029 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.0926 |

## Factory run u272 (measured from API usage)

| Date (UTC) | Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|---|
| 2026-11-10 | generation | deepseek-v4-pro | yes | 1755 | 19004 | 0 | 3200 | 0.0389 |
| 2026-11-10 | fix-1 | deepseek-flash | no | 18265 | 5743 | 0 | 134784 | 0.0066 |
| 2026-11-10 | fix-2 | deepseek-flash | no | 7732 | 1889 | 0 | 25344 | 0.0024 |
| 2026-11-10 | audit | deepseek-flash | no | 14798 | 18144 | 0 | 186368 | 0.0137 |
| 2026-11-10 | fix-3 | deepseek-flash | no | 9860 | 4954 | 0 | 79360 | 0.0047 |
| 2026-11-10 | fix-4 | deepseek-flash | no | 13328 | 2454 | 0 | 96896 | 0.0038 |
| 2026-11-10 | docs | deepseek-flash | no | 99726 | 12841 | 0 | 256 | 0.0227 |

Total: $0.0926. Prices: deepseek line, as measured by its adapter. Providers serve the current version of each model id, so the date tells which version answered; versions, launch stages and price sources per line are in the factory's model register (docs/MODELS.md).
