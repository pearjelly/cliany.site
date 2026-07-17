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

SITE_HTML="$ROOT_DIR/site/index.html"
SITE_JS="$ROOT_DIR/site/script.js"

assert_contains "$SITE_HTML" 'id="try-it"' "site exposes first-success anchor"
assert_contains "$SITE_HTML" 'id="feedback"' "site exposes feedback anchor"
assert_contains "$SITE_HTML" 'href="#try-it"' "site routes primary CTA to first success"
assert_contains "$SITE_HTML" 'href="#feedback"' "site navigation reaches feedback"
assert_contains "$SITE_HTML" 'data-clipboard="pip install cliany-site"' "site copies install command"
assert_contains "$SITE_HTML" 'data-clipboard="cliany-site doctor"' "site copies readiness command"
assert_contains "$SITE_HTML" 'data-clipboard="cliany-site cases"' "site copies case discovery command"

for template in bug_report.yml feature_request.yml case_proposal.yml; do
  assert_contains "$SITE_HTML" "issues/new?template=$template" "site links $template"
done

for key in nav.try nav.feedback hero.kicker try.title try.subtitle try.install.title try.install.body try.check.title try.check.body try.cases.title try.cases.body try.guide feedback.title feedback.subtitle feedback.bug.title feedback.bug.body feedback.bug.cta feedback.feature.title feedback.feature.body feedback.feature.cta feedback.case.title feedback.case.body feedback.case.cta footer.feedback; do
  if grep -F "'$key': { zh:" "$SITE_JS" | grep -Fq 'en:'; then
    pass "translation key $key has Chinese and English text"
  else
    fail "translation key $key has Chinese and English text"
  fi
done

if python3 - "$SITE_HTML" <<'PY'
from html.parser import HTMLParser
from pathlib import Path
import sys

class PageParser(HTMLParser):
    pass

PageParser().feed(Path(sys.argv[1]).read_text(encoding="utf-8"))
PY
then
  pass "site HTML parses with the standard library"
else
  fail "site HTML parses with the standard library"
fi

printf '\nSite conversion checks: %d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
