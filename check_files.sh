#!/usr/bin/env bash
# check_files.sh -- Post-write integrity check for all critical ITSMweb files.
# Run after any file modification. Exit code 0 = all clear; non-zero = failures found.
# Usage: ./check_files.sh
# From project root: bash check_files.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dir="${BASH_SOURCE[0]}"&&echo "$(dirname "$dir")")" && pwd)"
cd "$SCRIPT_DIR"

FAIL=0

check_tail() {
  local file="$1"; local min_lines="$2"; local expected_tail="$3"
  if [ ! -f "$file" ]; then
    echo "MISSING  $file"
    FAIL=1; return
  fi
  local lines
  lines=$(wc -l < "$file")
  local tail_content
  tail_content=$(tail -3 "$file")
  if [ "$lines" -lt "$min_lines" ]; then
    echo "TRUNCATED  $file  ($lines lines, expected >=$min_lines)"
    FAIL=1
  elif ! echo "$tail_content" | grep -q "$expected_tail"; then
    echo "BAD TAIL  $file  (last 3 lines do not contain '$expected_tail')"
    echo "          actual tail: $(tail -1 "$file")"
    FAIL=1
  else
    echo "OK  $file  ($lines lines)"
  fi
}

check_python() {
  local file="$1"; local min_lines="$2"
  if [ ! -f "$file" ]; then
    echo "MISSING  $file"
    FAIL=1; return
  fi
  local lines
  lines=$(wc -l < "$file")
  if [ "$lines" -lt "$min_lines" ]; then
    echo "TRUNCATED  $file  ($lines lines, expected >=$min_lines)"
    FAIL=1; return
  fi
  local result
  result=$(python3 -c "import ast; ast.parse(open('$file').read()); print('OK')" 2>&1)
  if [ "$result" != "OK" ]; then
    echo "SYNTAX ERR  $file: $result"
    FAIL=1
  else
    echo "OK  $file  ($lines lines)"
  fi
}

echo "=== ITSMweb file integrity check ==="
echo ""

echo "-- Templates --"
check_tail "app/templates/itsmbvf/base.html"           150  "</html>"
check_tail "app/templates/itsmbvf/calculators.html"    180  "endblock"
check_tail "app/templates/itsmbvf/step1_profile.html"   60  "endblock"
check_tail "app/templates/itsmbvf/step2_challenges.html" 70 "endblock"
check_tail "app/templates/itsmbvf/summary.html"        300  "endblock"
check_tail "app/templates/itsmbvf/assumptions.html"    150  "endblock"
check_tail "app/templates/itsmbvf/submitted.html"      100  "endblock"

echo ""
echo "-- Python modules --"
check_python "app/itsmbvf/routes.py"       500
check_python "app/itsmbvf/calculator.py"   200
check_python "app/itsmbvf/headers.py"       80
check_python "app/itsmbvf/report.py"       300
check_python "app/itsmbvf/emailer.py"      100
check_python "app/itsmbvf/data_capture.py" 150

echo ""
echo "-- Reference docs --"
check_tail "CLAUDE.md"           300  "."
check_tail "CLAUDE_problems.md"  700  "."
check_tail "PROJECT_STATE.md"    100  "."
check_tail "STANDING_RULES.md"    80  "."
check_tail "SESSION_LOG.md"      200  "."

echo ""
echo "-- Structural integrity --"
python3 "$(dirname "$0")/check_structure.py"
STR_RESULT=$?
if [ $STR_RESULT -ne 0 ]; then FAIL=1; fi

echo ""
echo "-- CSS coverage --"
python3 "$(dirname "$0")/check_css.py"
CSS_RESULT=$?
if [ $CSS_RESULT -ne 0 ]; then FAIL=1; fi

echo ""
echo ""
echo "-- JS function coverage --"
python3 "$(dirname "$0")/check_js.py"
JS_RESULT=$?
if [ $JS_RESULT -ne 0 ]; then FAIL=1; fi

echo ""
echo "-- Route smoke test --"
python3 "$(dirname "$0")/check_routes.py" 2>&1 | grep -v 'data_capture\|gspread\|name resolution'
ROUTE_RESULT=$?
if [ $ROUTE_RESULT -ne 0 ]; then FAIL=1; fi

if [ "$FAIL" -eq 0 ]; then
  echo "=== ALL FILES OK ==="
else
  echo "=== FAILURES DETECTED -- do not deploy ==="
  exit 1
fi
