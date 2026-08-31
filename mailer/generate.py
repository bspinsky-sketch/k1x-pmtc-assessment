"""Build the real Output Report PDF for one visitor's completed assessment.

Renders the 11 locked `output_report/*.tmpl.html` Jinja2 templates against
the visitor's real `results`/`goals`, then merges the rendered pages into
one PDF with headless Chromium via Playwright. This is not new rendering
logic -- it is `tools/preview_report.py`'s own `render_deck()`/
`try_build_pdf()` functions, already verified against 4 real
`run_calculation()` scenarios and real Google Sheet rows (see
PROJECT_STATE.md Open Item #2/#17, CLAUDE.md Key Decisions Log), ported
here to run inside the mailer instead of a standalone QA script.

Supersedes the earlier python-pptx placeholder (see git history for that
version, and CLAUDE_problems.md / SESSION_LOG.md for the 2026-08-31 switch).
The `generate(data, out_path)` signature is unchanged, but `out_path` is now
written directly as a PDF -- there is no intermediate deck format and no
LibreOffice conversion step. `output_report/` is baked into this image at
build time (see Dockerfile and infra/lib/mail-stack.ts) rather than fetched
at runtime, for the same reason the old placeholder baked in nothing that
needed a network call: nothing about generating a report should depend on
anything other than what shipped with the function.
"""

import json
import re
import shutil
import tempfile
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from pypdf import PdfWriter

TASK_DIR = Path(__file__).resolve().parent
OUTPUT_REPORT_DIR = TASK_DIR / "output_report"

PAGES = [
    "01-cover.tmpl.html", "02-goals.tmpl.html", "03-how-scored.tmpl.html",
    "04-capability.tmpl.html", "05-where-you-stand.tmpl.html", "06-solutions.tmpl.html",
    "07-roadmap.tmpl.html", "08-roadmap.tmpl.html", "09-roadmap.tmpl.html",
    "10-success-story.tmpl.html", "11-trust.tmpl.html",
]

# Matches the deck's own fixed canvas (base.css: `.page { width:1280px;
# height:720px; }`) at 96 DPI -- the same conversion tools/preview_report.py
# uses, so a page here is pixel-identical to what that tool already proved
# out against real data.
_PAGE_W_IN = 1280 / 96
_PAGE_H_IN = 720 / 96


def _level_desc_lookup():
    """Load CURRENT_DESCRIPTIONS out of roadmap_data.js, the same way
    tools/preview_report.py does -- the roadmap templates call
    level_desc(key, level) as a Jinja global, and this JS file (shared with
    the live assessment page's own maturity-curve JS) is the only place
    that copy lives."""
    js_src = (OUTPUT_REPORT_DIR / "assets" / "roadmap_data.js").read_text(encoding="utf-8")
    m = re.search(r"var CURRENT_DESCRIPTIONS = (\{.*?\n\});", js_src, re.DOTALL)
    assert m, "Could not locate CURRENT_DESCRIPTIONS in roadmap_data.js"
    current_descriptions = json.loads(m.group(1))

    def level_desc(key, level):
        return current_descriptions[key]["levels"][int(level)]

    return level_desc


def render_pages(results, goals, work_dir):
    """Render the 11 locked templates against real data into work_dir, with
    a real copy of assets/ alongside (a real copy, not a symlink -- see
    CLAUDE_problems.md's preview-tool symlink note; Lambda's /tmp doesn't
    support symlink games any better than Windows did). Returns the
    rendered .html paths in deck order."""
    env = Environment(loader=FileSystemLoader(str(OUTPUT_REPORT_DIR)))
    env.globals["level_desc"] = _level_desc_lookup()

    work_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(OUTPUT_REPORT_DIR / "assets", work_dir / "assets")

    generated_date = date.today().strftime("%B %-d, %Y")

    html_paths = []
    for page in PAGES:
        tmpl = env.get_template(page)
        html = tmpl.render(results=results, goals=goals, generated_date=generated_date)
        out_path = work_dir / page.replace(".tmpl.html", ".html")
        out_path.write_text(html, encoding="utf-8")
        html_paths.append(out_path)
    return html_paths


def render_pdf(html_paths, out_path, work_dir):
    """Merge the rendered pages into one PDF with headless Chromium.

    `--no-sandbox`/`--disable-dev-shm-usage` are not cosmetic: Lambda's
    container has no user namespaces for Chromium's own sandbox to use, and
    `/dev/shm` is tiny or absent, so real page content (this deck's
    background images/fonts) crashes Chromium without both flags. This is a
    documented Chromium-in-Lambda/container requirement, not something
    carried over from the cloud-workspace preview path, which runs on a
    normal Linux host and never needed either flag.

    `--single-process`/`--no-zygote`/`--disable-gpu` were added 2026-08-31 after
    the first real Lambda invocation: with only the two flags above, Chromium
    launched but then died before `new_page()` could run --
    `playwright._impl._errors.TargetClosedError: Browser.new_page: Target page,
    context or browser has been closed`. Root cause: Chromium's normal
    multi-process model forks a zygote process per tab/renderer, and that fork
    does not survive Lambda's restricted sandbox. `--single-process` keeps
    everything in one process (no fork needed) and `--no-zygote` disables the
    zygote pre-fork server directly; `--disable-gpu` removes another common
    crash source in headless containers with no GPU device. This combination is
    the standard, widely-documented fix for headless Chromium under AWS Lambda.
    """
    page_pdf_dir = work_dir / "_pdf_pages"
    page_pdf_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--single-process",
                "--no-zygote",
            ],
        )
        page = browser.new_page(
            viewport={"width": 1280, "height": 720}, device_scale_factor=2,
        )
        pdf_pages = []
        for i, html_path in enumerate(html_paths, 1):
            page.goto("file://" + str(html_path))
            page.wait_for_timeout(500)
            try:
                page.evaluate("document.fonts && document.fonts.ready")
            except Exception:
                pass
            page.wait_for_timeout(200)
            out_pdf = page_pdf_dir / f"{i:02d}.pdf"
            page.pdf(
                path=str(out_pdf), width=f"{_PAGE_W_IN}in", height=f"{_PAGE_H_IN}in",
                print_background=True,
                margin={"top": "0in", "bottom": "0in", "left": "0in", "right": "0in"},
            )
            pdf_pages.append(out_pdf)
        browser.close()

    writer = PdfWriter()
    for one_page_pdf in pdf_pages:
        writer.append(str(one_page_pdf))
    with open(out_path, "wb") as f:
        writer.write(f)
    return out_path


def generate(data, out_path):
    """Write the real 11-page Output Report PDF for one assessment to
    `out_path`.

    `data` is the payload `emailer.py` sends: the whole `run_calculation()`
    result under "results", the visitor's goal priorities under "goals"
    (needed by page 2), and lead-capture fields under "lead" (unused here --
    the report templates need the visitor's scores and goals, not their
    contact info). Read defensively -- a missing key here must not be the
    reason a visitor never gets their report.
    """
    results = data.get("results") or {}
    goals = data.get("goals") or {}

    with tempfile.TemporaryDirectory(dir="/tmp") as work:
        work_dir = Path(work)
        html_paths = render_pages(results, goals, work_dir)
        render_pdf(html_paths, out_path, work_dir)

    return out_path
