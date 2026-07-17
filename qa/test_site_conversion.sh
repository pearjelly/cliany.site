#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0
FAIL=0

pass() { printf '[PASS] %s\n' "$1"; PASS=$((PASS + 1)); }
fail() { printf '[FAIL] %s\n' "$1" >&2; FAIL=$((FAIL + 1)); }

assert_contains() {
  local file="$1" text="$2" label="$3"
  if grep -Fq -- "$text" "$file"; then pass "$label"; else fail "$label"; fi
}

assert_before() {
  local file="$1" first="$2" second="$3" label="$4"
  local first_line second_line
  first_line="$(grep -n -F -- "$first" "$file" | head -n 1 | cut -d: -f1 || true)"
  second_line="$(grep -n -F -- "$second" "$file" | head -n 1 | cut -d: -f1 || true)"
  if [ -n "$first_line" ] && [ -n "$second_line" ] && [ "$first_line" -lt "$second_line" ]; then
    pass "$label"
  else
    fail "$label"
  fi
}

assert_not_in_first_lines() {
  local file="$1" text="$2" label="$3"
  if head -n 35 "$file" | grep -Fq -- "$text"; then fail "$label"; else pass "$label"; fi
}

for template in bug_report.yml feature_request.yml case_proposal.yml; do
  if [ -f "$ROOT_DIR/.github/ISSUE_TEMPLATE/$template" ]; then
    pass "tracked issue template: $template"
  else
    fail "tracked issue template: $template"
  fi
done

for readme in README.md README.zh.md; do
  path="$ROOT_DIR/$readme"
  feature_heading="## Features"
  if [ "$readme" = "README.zh.md" ]; then feature_heading="## 特性"; fi
  assert_contains "$path" "pip install cliany-site" "$readme installs from PyPI"
  assert_contains "$path" "cliany-site doctor" "$readme explains doctor"
  assert_contains "$path" "cliany-site cases" "$readme explains maintained cases"
  assert_before "$path" "## Start here" "$feature_heading" "$readme puts onboarding before features"
  assert_not_in_first_lines "$path" "v0.14" "$readme removes old v0.14 notices from its opening"
done

for readme in README.md README.zh.md; do
  path="$ROOT_DIR/$readme"
  for template in bug_report.yml feature_request.yml case_proposal.yml; do
    assert_contains "$path" "issues/new?template=$template" "$readme links $template"
  done
done

printf '\nSite conversion checks: %d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
