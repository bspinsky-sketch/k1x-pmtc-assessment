"""
check_js.py -- Verify every JS function referenced from an inline event
attribute (onclick=, onsubmit=, etc.) in each template is defined somewhere
in that same template's own <script> block(s).

K1x PMTC Assessment's pages wire most interactivity via addEventListener,
not inline handlers, so this check's surface is small (results.html's
modal open/close and form-submit gate are the main ones) -- but it's cheap
and still catches a truncated/renamed handler.

Rewritten 2026-08-27 -- the previous version assumed the prior project's
(itsmbvf) multi-template-sharing-globals structure. See PROJECT_STATE.md
Open Item #3.

Exit 0 = all calls covered; 1 = gaps found.
"""

import re, sys
from pathlib import Path

BASE_DIR  = Path(__file__).parent
TEMPLATES = sorted((BASE_DIR / 'app/templates/pmtc').glob('*.html'))

# Browser/runtime builtins that can legitimately appear in an inline handler.
GLOBAL_FUNS = {
    'alert', 'confirm', 'console', 'setTimeout', 'setInterval', 'clearTimeout',
    'parseInt', 'parseFloat', 'Math', 'JSON', 'Object', 'Array', 'String',
    'Number', 'document', 'window', 'fetch', 'Promise', 'encodeURIComponent',
}

def extract_calls(text):
    calls = set()
    for attr in re.findall(r'on\w+="([^"]*)"', text):
        for name in re.findall(r'\b([a-zA-Z_]\w*)\s*\(', attr):
            calls.add(name)
    return calls

def extract_definitions(text):
    defs = set()
    for script in re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL):
        for name in re.findall(r'function\s+([a-zA-Z_]\w*)\s*\(', script):
            defs.add(name)
    return defs

def main():
    if not TEMPLATES:
        print('ERROR: no templates found under app/templates/pmtc/')
        sys.exit(1)

    print('JS function check (per-file, inline event handlers only)')
    fail = False
    total_calls = 0
    for tmpl in TEMPLATES:
        text = tmpl.read_text(encoding='utf-8', errors='replace')
        calls = extract_calls(text)
        defs = extract_definitions(text) | GLOBAL_FUNS
        missing = sorted(c for c in calls if c not in defs)
        total_calls += len(calls)
        if missing:
            print(f'  FAIL  {tmpl.name}')
            for m in missing:
                print(f'    {m}() called but not defined in this file')
            fail = True
        elif calls:
            print(f'  OK    {tmpl.name}  ({len(calls)} call(s) verified)')
        else:
            print(f'  OK    {tmpl.name}  (no inline event handlers)')

    print()
    if fail:
        print('RESULT: FAIL -- undefined JS functions found')
        sys.exit(1)
    else:
        print(f'RESULT: PASS -- all {total_calls} inline JS function call(s) are defined')
        sys.exit(0)

if __name__ == '__main__':
    main()
