"""
check_css.py -- Verify every CSS class used in templates is defined in base.html.

Extracts:
  - All class names from HTML/Jinja2 template files (skips Jinja2 expressions)
  - All CSS selectors from the <style> block in base.html

Reports any class present in templates but missing from base.html CSS.
Exit code 0 = all classes covered; 1 = gaps found.
"""

import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
TEMPLATES = list((BASE_DIR / 'app/templates/itsmbvf').glob('*.html'))
BASE_TEMPLATES = [
    BASE_DIR / 'app/templates/itsmbvf/base.html',
    BASE_DIR / 'app/templates/itsmbvf/modal_base.html',
]

# Known false positives -- classes added dynamically via JS, Bootstrap remnants
# in submitted.html (legacy), or framework-injected classes we don't control
IGNORE = {
    # Bootstrap classes in submitted.html (legacy page, not rebuilt)
    'badge', 'bg-secondary', 'btn-lg', 'btn-outline-secondary', 'btn-sm',
    'card', 'card-body', 'col-6', 'col-md-4', 'col-lg-3', 'col-lg-9',
    'col-md-5', 'col-md-7', 'd-flex', 'form-control', 'fs-3', 'fw-bold',
    'fw-semibold', 'gap-2', 'gap-3', 'h-100', 'mb-3', 'mb-4', 'mb-md-0',
    'py-3', 'px-5', 'row', 'shadow-sm', 'text-center', 'text-white',
    'align-items-start', 'align-items-center', 'mb-1', 'mb-2', 'bvf-btn',
    # Flash categories injected at runtime by Flask
    'danger', 'success', 'warning', 'info',
    # Jinja2 conditional classes (dynamic, checked separately)
    'active', 'done', 'open', 'visible', 'show',
    # Chart.js canvas -- no CSS class needed
    # index.html and submitted.html legacy Bootstrap classes (pages not yet rebuilt)
    'bg-light', 'container', 'h3', 'mt-5', 'p-4', 'text-muted', 'text-success',
    'mb-0', 'g-3', 'justify-content-center', 'small', 'table', 'table-sm',
}

def extract_template_classes():
    """Extract all static class names from template files."""
    used = set()
    # Match class="..." -- skip anything containing {{ (Jinja2 expression)
    class_attr = re.compile(r'class="([^"]*)"')
    jinja_expr = re.compile(r'\{[{%]')
    for tmpl in TEMPLATES:
        text = tmpl.read_text(encoding='utf-8', errors='replace')
        for m in class_attr.finditer(text):
            val = m.group(1)
            if jinja_expr.search(val):
                # Extract the static prefix before any Jinja2 expression
                static_part = val[:jinja_expr.search(val).start()].strip()
                for cls in static_part.split():
                    used.add(cls)
            else:
                for cls in val.split():
                    used.add(cls)
    return used

def extract_defined_classes():
    """Extract all CSS class selectors defined in any base template <style> block."""
    defined = set()
    for base_tmpl in BASE_TEMPLATES:
        if not base_tmpl.exists():
            continue
        text = base_tmpl.read_text(encoding='utf-8', errors='replace')
        style_match = re.search(r'<style>(.*?)</style>', text, re.DOTALL)
        if not style_match:
            continue
        css = style_match.group(1)
        for m in re.finditer(r'\.([\w-]+)', css):
            defined.add(m.group(1))
    if not defined:
        print('ERROR: No <style> blocks found in any base template')
        import sys; sys.exit(1)
    return defined
def main():
    used    = extract_template_classes()
    defined = extract_defined_classes()

    # Remove ignored classes
    used -= IGNORE

    missing = sorted(used - defined)

    print(f'CSS coverage check')
    print(f'  Template classes found : {len(used)}')
    print(f'  CSS classes defined    : {len(defined)}')
    print()

    if missing:
        print(f'MISSING from base.html CSS ({len(missing)}):')
        for cls in missing:
            # Show which template(s) use it
            users = []
            class_attr = re.compile(r'class="([^"]*)"')
            for tmpl in TEMPLATES:
                text = tmpl.read_text(encoding='utf-8', errors='replace')
                if re.search(r'class="[^"]*\b' + re.escape(cls) + r'\b', text):
                    users.append(tmpl.name)
            print(f'  .{cls}  <-- {", ".join(users)}')
        print()
        print('RESULT: FAIL -- add missing rules to base.html before deploying')
        sys.exit(1)
    else:
        print('RESULT: PASS -- all template classes are defined in base.html')
        sys.exit(0)

if __name__ == '__main__':
    main()
