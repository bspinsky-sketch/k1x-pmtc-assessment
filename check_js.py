"""
check_js.py -- Verify every JS function called in templates is defined somewhere.

Extracts:
  - Function calls from onclick/onchange/onsubmit/oninput event attributes
  - Function definitions from <script> blocks in each template

Flags any called function with no matching definition.
Exit 0 = all calls covered; 1 = gaps found.
"""

import re, sys
from pathlib import Path

BASE_DIR  = Path(__file__).parent
TEMPLATES = list((BASE_DIR / 'app/templates/itsmbvf').glob('*.html'))

# Known globals: browser built-ins, Chart.js, and other CDN library functions
GLOBAL_FUNS = {
    'alert','confirm','console','setTimeout','setInterval','clearTimeout',
    'parseInt','parseFloat','Math','JSON','Object','Array','String','Number',
    'document','window','fetch','Promise','encodeURIComponent',
    # Chart.js
    'Chart',
    # Our own top-level helpers that appear across templates
    'fmtDollars', 'buildChart', 'showBenefit', 'setPri', 'openBM', 'closeBM',
}

def extract_calls(text):
    """Extract function names from event handler attributes."""
    calls = set()
    # onclick="fnName(...)" -- grab the function name before the first '('
    for attr in re.findall(r'on\w+="([^"]*)"', text):
        for name in re.findall(r'\b([a-zA-Z_]\w*)\s*\(', attr):
            calls.add(name)
    return calls

def extract_definitions(text):
    """Extract function names defined in <script> blocks."""
    defs = set()
    for script in re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL):
        for name in re.findall(r'function\s+([a-zA-Z_]\w*)\s*\(', script):
            defs.add(name)
    return defs

def main():
    # Collect all definitions across all templates (functions are globally available)
    all_defs = set(GLOBAL_FUNS)
    for tmpl in TEMPLATES:
        text = tmpl.read_text(encoding='utf-8', errors='replace')
        all_defs |= extract_definitions(text)

    print('JS function check')
    print(f'  Functions defined (incl. globals): {len(all_defs)}')

    fail = False
    for tmpl in TEMPLATES:
        text = tmpl.read_text(encoding='utf-8', errors='replace')
        calls = extract_calls(text)
        missing = sorted(c for c in calls if c not in all_defs)
        if missing:
            print(f'  FAIL  {tmpl.name}')
            for m in missing:
                print(f'    {m}() called but not defined')
            fail = True
        elif calls:
            print(f'  OK    {tmpl.name}  ({len(calls)} call(s) verified)')

    print()
    if fail:
        print('RESULT: FAIL -- undefined JS functions found')
        sys.exit(1)
    else:
        print('RESULT: PASS -- all JS function calls are defined')
        sys.exit(0)

if __name__ == '__main__':
    main()
