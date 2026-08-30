#!/usr/bin/env python3
"""
Standalone, read-only QA/preview tool for the K1x PMTC Output Report deck.

Pulls one real visitor's raw inputs from the Google Sheet (the same columns
data_capture.py already writes -- Company/Industry/6 goal weights/10
capability levels, Sheet columns C:T), re-runs them through the real
calculator.run_calculation() to get a genuine results dict, then renders
the same 11 locked *.tmpl.html Jinja2 templates built and verified for
Open Item #2 against synthetic scenarios.

Deliberately does NOT touch routes.py, results.html, or mailer/generate.py
-- this is a QA tool, not the live delivery path. Read-only against the
Sheet: it only ever calls get()/col_values(), never update()/append_row().

Usage:
  python3 tools/preview_report.py --list [--n 15]
      List the most recent captured rows (row number, timestamp, company,
      industry) so you can pick one.

  python3 tools/preview_report.py --row 42
      Render the 11-page deck for that row's real data into
      tools/preview_output/<row>_<company-slug>/*.html

  python3 tools/preview_report.py --row 42 --pdf
      Also merge the 11 pages into a single PDF. Requires Playwright --
      if it's not installed, the script prints the pip/install-chromium
      command and skips the PDF step (the rendered HTML pages are still
      produced either way).

Credentials: reads GOOGLE_CREDENTIALS_JSON / GOOGLE_SHEET_ID from
app/.env, exactly like the live app -- no separate setup needed.
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
APP_DIR = TOOLS_DIR.parent / "app"
BLUEPRINT_DIR = APP_DIR / "app" / "blueprints" / "pmtc"
OUTPUT_REPORT_DIR = TOOLS_DIR.parent / "output_report"
PREVIEW_OUT_DIR = TOOLS_DIR / "preview_output"

DATA_START_ROW = 4  # rows 1-3 are title/headers -- must match data_capture.py

# Must match data_capture.py's GOAL_KEYS_ORDER / CAPABILITY_KEYS_ORDER
# exactly (Sheet columns E:J and K:T respectively, i.e. C:T once Company/
# Industry are included at the front).
GOAL_KEYS_ORDER = [
    "reduce_time", "standardize", "scalable_growth",
    "accuracy", "client_experience", "advisory_services",
]
CAPABILITY_KEYS_ORDER = [
    "document_intake", "inventory_management", "data_extraction",
    "data_validation", "data_review", "tax_analysis_reporting",
    "integration", "resource_structure", "advisory", "governance_trust",
]

PAGES = [
    "01-cover.tmpl.html", "02-goals.tmpl.html", "03-how-scored.tmpl.html",
    "04-capability.tmpl.html", "05-where-you-stand.tmpl.html", "06-solutions.tmpl.html",
    "07-roadmap.tmpl.html", "08-roadmap.tmpl.html", "09-roadmap.tmpl.html",
    "10-success-story.tmpl.html", "11-trust.tmpl.html",
]


def load_calculator():
    """Import calculator.py standalone, by file path. It's pure Python
    with no Flask dependency, so this reaches run_calculation() without
    needing the full app package or a Flask app context."""
    spec = importlib.util.spec_from_file_location(
        "pmtc_calculator", BLUEPRINT_DIR / "calculator.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_credentials():
    """Same credential source the live app uses -- app/.env, read-only."""
    from dotenv import load_dotenv
    load_dotenv(APP_DIR / ".env")
    creds_raw = os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip()
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    if not creds_raw or not sheet_id:
        sys.exit(
            "GOOGLE_CREDENTIALS_JSON / GOOGLE_SHEET_ID not found in app/.env -- "
            "this tool reads the same credentials the live app uses and can't "
            "proceed without them."
        )
    return creds_raw, sheet_id


def connect_sheet():
    import gspread
    from google.oauth2.service_account import Credentials

    creds_raw, sheet_id = load_credentials()
    creds_dict = json.loads(creds_raw)
    # Read-only scope deliberately -- this tool never writes to the Sheet.
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    return gc.open_by_key(sheet_id).sheet1


def list_recent_rows(sheet, n=15):
    """Read-only. Shows row number, timestamp, company, industry for the
    most recent n captured rows so you can pick one to preview."""
    timestamps = sheet.col_values(2)  # column B
    last_row = len(timestamps)  # 1-indexed: last populated row in col B
    if last_row < DATA_START_ROW:
        print("No captured rows found (Sheet has no data yet from row 4 on).")
        return
    start_row = max(DATA_START_ROW, last_row - n + 1)
    values = sheet.get(f"B{start_row}:D{last_row}")

    print(f"{'Row':>5}  {'Timestamp':<20}  {'Company':<30}  Industry")
    for i, row in enumerate(values):
        row_number = start_row + i
        timestamp = row[0] if len(row) > 0 else ""
        company = row[1] if len(row) > 1 else ""
        industry = row[2] if len(row) > 2 else ""
        if not timestamp and not company:
            continue
        print(f"{row_number:>5}  {timestamp:<20}  {company:<30}  {industry}")


def load_row(sheet, row_number):
    """Read-only. Pulls one row's raw inputs (Company, Industry, 6 goal
    weights, 10 capability levels -- Sheet columns C:T) and reconstructs
    the exact (company, industry, goals, ratings) shape run_calculation()
    expects."""
    values = sheet.get(f"C{row_number}:T{row_number}")
    if not values or not values[0]:
        sys.exit(f"Row {row_number} appears empty (Sheet columns C:T) -- check the row number with --list.")
    row = values[0]
    row = row + [""] * (18 - len(row))  # pad -- trailing blanks may be trimmed by the API
    company = row[0]
    industry = row[1]
    goal_values = row[2:8]
    capability_values = row[8:18]

    goals = {}
    for key, raw in zip(GOAL_KEYS_ORDER, goal_values):
        goals[key] = int(raw) if str(raw).strip() != "" else 0
    ratings = {}
    for key, raw in zip(CAPABILITY_KEYS_ORDER, capability_values):
        ratings[key] = int(raw) if str(raw).strip() != "" else 0

    return company, industry, goals, ratings


def render_deck(results, goals, out_dir):
    from jinja2 import Environment, FileSystemLoader

    with open(OUTPUT_REPORT_DIR / "assets" / "roadmap_data.js", encoding="utf-8") as f:
        js_src = f.read()
    m = re.search(r"var CURRENT_DESCRIPTIONS = (\{.*?\n\});", js_src, re.DOTALL)
    assert m, "Could not locate CURRENT_DESCRIPTIONS in roadmap_data.js"
    current_descriptions = json.loads(m.group(1))

    def level_desc(key, level):
        return current_descriptions[key]["levels"][int(level)]

    env = Environment(loader=FileSystemLoader(str(OUTPUT_REPORT_DIR)))
    env.globals["level_desc"] = level_desc

    out_dir.mkdir(parents=True, exist_ok=True)
    # A real copy, not a symlink -- Windows symlink/junction creation needs
    # Developer Mode or admin rights, and even when it succeeds it isn't
    # portable: it works fine opened locally but is unreadable through some
    # other views of the same folder (confirmed 2026-08-30, see
    # CLAUDE_problems.md/SESSION_LOG.md). Copying is a small, cheap price
    # (~1.6MB) for output that works everywhere without caveats.
    assets_dir = out_dir / "assets"
    if not assets_dir.exists():
        shutil.copytree(OUTPUT_REPORT_DIR / "assets", assets_dir)

    generated_date = (
        date.today().strftime("%B %-d, %Y") if os.name != "nt"
        else date.today().strftime("%B %d, %Y")
    )

    html_paths = []
    for page in PAGES:
        tmpl = env.get_template(page)
        html = tmpl.render(results=results, goals=goals, generated_date=generated_date)
        out_name = page.replace(".tmpl.html", ".html")
        out_path = out_dir / out_name
        out_path.write_text(html, encoding="utf-8")
        html_paths.append(out_path)

    return html_paths


def try_build_pdf(html_paths, out_dir, company):
    try:
        from playwright.sync_api import sync_playwright
        from pypdf import PdfWriter
    except ImportError as exc:
        print(
            f"\nPDF export skipped: {exc.name or 'a required package'} isn't installed here.\n"
            "  pip3 install playwright pypdf && python3 -m playwright install chromium\n"
            "The 11 rendered .html pages above are already usable on their own --\n"
            "open any of them directly in a browser."
        )
        return None

    page_pdf_dir = out_dir / "_pdf_pages"
    page_pdf_dir.mkdir(exist_ok=True)
    width_in = 1280 / 96
    height_in = 720 / 96

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
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
                path=str(out_pdf), width=f"{width_in}in", height=f"{height_in}in",
                print_background=True,
                margin={"top": "0in", "bottom": "0in", "left": "0in", "right": "0in"},
            )
            pdf_pages.append(out_pdf)
        browser.close()

    writer = PdfWriter()
    for p_ in pdf_pages:
        writer.append(str(p_))
    slug = re.sub(r"[^A-Za-z0-9]+", "_", company).strip("_") or "report"
    final_path = out_dir / f"{slug}_PMTC_Capability_Report_PREVIEW.pdf"
    with open(final_path, "wb") as f:
        writer.write(f)
    return final_path


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--list", action="store_true", help="List recent captured rows")
    parser.add_argument("--n", type=int, default=15, help="How many recent rows to list (default 15)")
    parser.add_argument("--row", type=int, help="Sheet row number to preview (see --list)")
    parser.add_argument("--pdf", action="store_true", help="Also merge the 11 pages into one PDF")
    parser.add_argument("--out", type=str, default=None,
                         help="Output directory (default: tools/preview_output/<row>_<company>)")
    args = parser.parse_args()

    sheet = connect_sheet()

    if args.list or not args.row:
        list_recent_rows(sheet, n=args.n)
        if not args.row:
            print("\nPass --row <N> to render that row's real deck.")
            return

    calculator = load_calculator()
    company, industry, goals, ratings = load_row(sheet, args.row)
    print(f"Row {args.row}: {company!r} / {industry!r}")
    print(f"  goals:    {goals}")
    print(f"  ratings:  {ratings}")

    results = calculator.run_calculation(company, industry, goals, ratings)
    print(f"  your_score={results['your_score']}  peer_score={results['peer_score']}  band={results['band_name']!r}")

    slug = re.sub(r"[^A-Za-z0-9]+", "_", company).strip("_") or "row"
    out_dir = Path(args.out) if args.out else PREVIEW_OUT_DIR / f"{args.row}_{slug}"
    html_paths = render_deck(results, goals, out_dir)
    print(f"\nRendered 11 pages to: {out_dir}")

    if args.pdf:
        pdf_path = try_build_pdf(html_paths, out_dir, company)
        if pdf_path:
            print(f"PDF: {pdf_path}")


if __name__ == "__main__":
    main()
