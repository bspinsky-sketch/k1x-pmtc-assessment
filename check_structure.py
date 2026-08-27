"""
check_structure.py -- Detect middle-truncation by comparing structural fingerprints.

After every verified write, run with --update to store a new baseline.
On every check run, compares current counts against baseline and flags drops.

Structural markers counted per file:
  .html templates : CSS class definitions (each template's own <style>
                     block -- there is no shared base.html in this project,
                     each page is fully self-contained), CSS rule count,
                     JS function definitions, Jinja2 block/for/if tags
  .py modules     : function definitions (def ), class definitions
                     (class ), @bp.route(...) decorator count

Usage:
  python3 check_structure.py          # compare against baseline
  python3 check_structure.py --update # rewrite baseline from current files
"""

import re, sys, json
from pathlib import Path

BASE_DIR  = Path(__file__).parent
BASELINE  = BASE_DIR / '.check_baseline.json'

# K1x PMTC Assessment file set (Phase 2/3/4). Rewritten 2026-08-27 -- the
# previous version of this file hardcoded a prior project's (itsmbvf)
# paths, which don't exist here. See PROJECT_STATE.md Open Item #3.
FILES = {
    'app/templates/pmtc/profile.html':      'html',
    'app/templates/pmtc/assessment.html':   'html',
    'app/templates/pmtc/results.html':      'html',
    'app/blueprints/pmtc/routes.py':        'py',
    'app/blueprints/pmtc/calculator.py':    'py',
    'app/blueprints/pmtc/data_capture.py':  'py',
    'app/blueprints/pmtc/emailer.py':       'py',
    'app/blueprints/pmtc/report.py':        'py',
}

def fingerprint(path_str, kind):
    path = BASE_DIR / path_str
    text = path.read_text(encoding='utf-8', errors='replace')
    fp = {'lines': text.count('\n')}

    if kind == 'html':
        fp['jinja_for']       = len(re.findall(r'\{%-?\s*for\b',     text))
        fp['jinja_endfor']    = len(re.findall(r'\{%-?\s*endfor\b',  text))
        fp['jinja_if']        = len(re.findall(r'\{%-?\s*if\b',      text))
        fp['jinja_endif']     = len(re.findall(r'\{%-?\s*endif\b',   text))
        fp['css_classes']     = len(re.findall(r'\.([\w-]+)\s*\{',   text))
        style = re.search(r'<style>(.*?)</style>', text, re.DOTALL)
        fp['css_rules']       = text.count('{') - text.count('{{')
        fp['css_class_count'] = len(re.findall(r'\.([\w-]+)', style.group(1))) if style else 0
        fp['js_functions']    = len(re.findall(r'function\s+\w+\s*\(', text))

    elif kind == 'py':
        fp['functions'] = len(re.findall(r'^\s*def \w+', text, re.MULTILINE))
        fp['classes']   = len(re.findall(r'^\s*class \w+', text, re.MULTILINE))
        fp['routes']    = len(re.findall(r'@bp\.route\(', text))

    return fp

def load_baseline():
    if not BASELINE.exists():
        return {}
    return json.loads(BASELINE.read_text())

def save_baseline(data):
    BASELINE.write_text(json.dumps(data, indent=2))

def compare(key, current, stored):
    issues = []
    for metric, cur_val in current.items():
        if metric not in stored:
            continue
        stored_val = stored[metric]
        if cur_val < stored_val:
            issues.append(f'  {metric}: was {stored_val}, now {cur_val} (DROP OF {stored_val - cur_val})')
    return issues

def main():
    update_mode = '--update' in sys.argv

    if update_mode:
        baseline = {}
        for path_str, kind in FILES.items():
            baseline[path_str] = fingerprint(path_str, kind)
        save_baseline(baseline)
        print(f'Baseline updated -- {len(FILES)} files fingerprinted')
        for f, fp in baseline.items():
            print(f'  {f}: {fp}')
        sys.exit(0)

    baseline = load_baseline()
    if not baseline:
        print('No baseline found -- run with --update after a verified-good state')
        print('Skipping structural check')
        sys.exit(0)

    print('Structural integrity check')
    fail = False
    for path_str, kind in FILES.items():
        current = fingerprint(path_str, kind)
        stored  = baseline.get(path_str, {})
        if not stored:
            print(f'  NO BASELINE  {path_str}')
            continue
        issues = compare(path_str, current, stored)
        if issues:
            print(f'  FAIL  {path_str}')
            for issue in issues:
                print(issue)
            fail = True
        else:
            print(f'  OK    {path_str}')

    print()
    if fail:
        print('RESULT: FAIL -- structural drop detected; possible middle truncation')
        sys.exit(1)
    else:
        print('RESULT: PASS -- all structural counts at or above baseline')
        sys.exit(0)

if __name__ == '__main__':
    main()
