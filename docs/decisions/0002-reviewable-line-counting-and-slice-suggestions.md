# Reviewable line counting and slice suggestions

Status: accepted (generated, pending human review)

## Context

Large pull requests get slower reviews. Existing CI size checks either count lock files/generated code or only say 'too big' without helping. We need a library that counts only reviewable lines, gives clear thresholds, and proposes directory-based splits.

## Decision

Implement a pure-Python, stdlib-only package. Count lines as added+deleted for non-binary, non-ignored files. Ignore patterns support basename glob and directory segment matching only. Suggest slices by first-fit decreasing directory groups with oversized groups kept separate. Expose CLI returning exit codes 0/1/2.

## Consequences

Reviewers get an accurate measure and actionable split suggestions. The strict ignore pattern grammar (two forms) prevents complex regex errors. Binary files count zero lines and are excluded from file count, matching their non-reviewable nature.
