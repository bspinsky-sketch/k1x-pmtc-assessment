"""
check_css.py -- Verify every CSS class used in each template is defined in
that same template's own <style> block.

K1x PMTC Assessment's three pages (profile/assessment/results) are each
fully self-contained -- no shared base.html, no {% extends %} (base.html
and the other starter templates were deleted in Phase 3) -- so CSS coverage
is checked per-file rather than against one shared stylesheet.

Rewritten 2026-08-27 -- the previous version of this file assumed the
prior project's (itsmbvf) base.html + N-child-templates structure, which
doesn't apply here. See PROJECT_STATE.md Open Item #3.

Exit code 0 = all classes covered; 1 = gaps found.
"""

import re
import sys
from pathlib import Path

BASE_DIR  = Path(__file__).parent
TEMPLATES = sorted((BASE_DIR / 'app/templates/pmtc').glob('*.html'))

# Classes toggled purely via JS (classList.add/remove, never present in this
# file's own class="..." attributes at rest) go here if a real FAIL below
# turns out to be a false positive.
#
# 'done' -- applied to completed breadcrumb steps (assessment.html,
# results.html: class="bc-step done bc-link") but was never given a CSS
# rule in the approved wireframe either (verified against
# wireframe/assessment.html and wireframe/results.html directly -- no
# .done{...} rule exists there, so this is inherited, not a porting
# defect). Currently a harmless no-op class. 2026-08-27.
IGNORE = {'done'}

class_attr_re = re.compile(r'class="([^"]*)"')
jinja_expr_re = re.compile(r'\{[{%]')

script_re = re.compile(r'<script\b[^>]*>.*?</script>', re.DOTALL)

def extract_used_classes(text):
    # Strip <script> blocks first -- this project's pages build HTML via JS
    # string concatenation / template literals (e.g. results.html's bar
    # chart: '<div class="bar-user ' + (ahead ? 'ahead' : 'behind') + ...'),
    # which the naive class="..." regex below would otherwise misparse as
    # HTML markup and flag as garbage "used classes". Only literal HTML
    # markup should count.
    html_only = script_re.sub('', text)
    used = set()
    for m in class_attr_re.finditer(html_only):
        val = m.group(1)
        jm = jinja_expr_re.search(val)
        static_part = val[:jm.start()] if jm else val
        for cls in static_part.split():
            used.add(cls)
    return used

def extract_defined_classes(text):
    style_match = re.search(r'<style>(.*?)</style>', text, re.DOTALL)
    if not style_match:
        return set()
    css = style_match.group(1)
    return {m.group(1) for m in re.finditer(r'\.([\w-]+)', css)}

def main():
    if not TEMPLATES:
        print('ERROR: no templates found under app/templates/pmtc/')
        sys.exit(1)

    print('CSS coverage check (per-file -- each page owns its own <style>)')
    fail = False
    for tmpl in TEMPLATES:
        text = tmpl.read_text(encoding='utf-8', errors='replace')
        used = extract_used_classes(text) - IGNORE
        defined = extract_defined_classes(text)
        if not defined:
            print(f'  FAIL  {tmpl.name}  -- no <style> block found')
            fail = True
            continue
        missing = sorted(used - defined)
        if missing:
            print(f'  FAIL  {tmpl.name}  ({len(missing)} missing of {len(used)} used, {len(defined)} defined)')
            for cls in missing:
                print(f'    .{cls}')
            fail = True
        else:
            print(f'  OK    {tmpl.name}  ({len(used)} used, {len(defined)} defined)')

    print()
    if fail:
        print('RESULT: FAIL -- add missing rules, or extend IGNORE if truly JS-only, before deploying')
        sys.exit(1)
    else:
        print('RESULT: PASS -- all template classes are defined in their own <style> block')
        sys.exit(0)

if __name__ == '__main__':
    main()
