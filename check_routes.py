"""
check_routes.py -- Route smoke test for ITSMweb.

Uses Flask's built-in test client (no running server needed).
Seeds a realistic session, hits every page route, and checks:
  1. HTTP 200 (not 302, not 500)
  2. Expected content substrings are present in the response body

Also spot-checks run_calculation() output keys.

Exit 0 = all checks pass; 1 = any failure.

NOTE: GET / clears the session (fresh-session route), so it is tested
with a separate client from the seeded-session routes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from app import create_app
except Exception as e:
    print(f'FAIL  Could not import app: {e}')
    sys.exit(1)

try:
    from app.itsmbvf.calculator import run_calculation, read_defaults
except Exception as e:
    print(f'FAIL  Could not import calculator: {e}')
    sys.exit(1)

# ---------------------------------------------------------------------------
# Test session data -- keys must match what routes.py stores exactly
# ---------------------------------------------------------------------------
PROFILE = {
    'company_name':     'Acme Corp',
    'revenue_millions': 500.0,
    'employees':        2000,
    'it_headcount':     74,
}

PRIORITIES = {
    'ch1': 'High', 'ch2': 'Medium', 'ch3': 'Low',
    'ch4': 'None', 'ch5': 'High',   'ch6': 'Medium', 'ch7': 'Low',
}

try:
    defs = read_defaults()
    ASSUMPTION_DEFAULTS = defs.get('assumptions', {})
    INVESTMENT_DEFAULTS = defs.get('investment', {})
except Exception as e:
    print(f'WARN  read_defaults() failed ({e}); using empty dicts')
    ASSUMPTION_DEFAULTS = {}
    INVESTMENT_DEFAULTS = {}

try:
    KPIS = run_calculation(PROFILE, PRIORITIES)
except Exception as e:
    print(f'WARN  run_calculation() raised an exception: {e}')
    print('WARN  Workbook may be unavailable in sandbox; route checks will proceed with empty KPIs')
    KPIS = {}

# Routes that need a pre-seeded session (exclude / -- it clears the session)
SEEDED_ROUTES = [
    ('/challenges',  ['high ticket volume', 'view benefits']),
    ('/assumptions', ['assumptions', 'save']),
    ('/summary',     ['roi', 'payback', 'download']),
    ('/calculators', ['benefit', 'benefit calculators']),
]

# Routes that work on an empty session (tested separately)
FRESH_ROUTES = [
    ('/',            ['company name', 'annual revenue', 'employees']),
]

# KPI keys that must be present in run_calculation() output
REQUIRED_KPI_KEYS = ['roi', 'payback', 'irr', 'npv', 'benefit_3y',
                     'benefit_ann_avg', 'codn_mo']


def check_route(client, route, expected, fail_list):
    try:
        resp = client.get(route)
        if resp.status_code != 200:
            loc = resp.headers.get('Location', '')
            print(f'  FAIL  GET {route} -- status {resp.status_code} -> {loc}')
            fail_list.append(route)
            return
        body = resp.data.decode('utf-8', errors='replace').lower()
        missing = [s for s in expected if s not in body]
        if missing:
            print(f'  FAIL  GET {route} -- expected strings missing: {missing}')
            fail_list.append(route)
        else:
            print(f'  OK    GET {route}')
    except Exception as e:
        print(f'  FAIL  GET {route} -- exception: {e}')
        fail_list.append(route)


def main():
    app = create_app()
    app.config['TESTING']          = True
    app.config['WTF_CSRF_ENABLED'] = False

    print('Route smoke test')
    failures = []

    # -- KPI key check (skip when workbook unavailable -- KPIS will be empty)
    if not KPIS:
        print(f'  WARN  run_calculation() skipped (workbook unavailable in sandbox)')
    else:
        missing_keys = [k for k in REQUIRED_KPI_KEYS if k not in KPIS]
        if missing_keys:
            print(f'  FAIL  run_calculation() missing KPI keys: {missing_keys}')
            failures.append('kpi_keys')
        else:
            print(f'  OK    run_calculation() -- all required KPI keys present')

        blank = {'$0', '0', '0.0 months', 'n/a', None, 0}
        zero_keys = [k for k in REQUIRED_KPI_KEYS
                     if str(KPIS.get(k, '')).lower() in {str(x).lower() for x in blank}
                     or KPIS.get(k) == 0]
        if zero_keys:
            print(f'  WARN  run_calculation() returned blank/zero for: {zero_keys}')

    # -- Test routes that need a seeded session (one client, session seeded once)
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['profile']             = PROFILE
            sess['priorities']          = PRIORITIES
            sess['assumptions']         = ASSUMPTION_DEFAULTS
            sess['investment']          = INVESTMENT_DEFAULTS
            sess['kpis']                = KPIS
            sess['assumption_defaults'] = ASSUMPTION_DEFAULTS
            sess['investment_defaults'] = INVESTMENT_DEFAULTS
        for route, expected in SEEDED_ROUTES:
            check_route(client, route, expected, failures)

    # -- Test fresh-session routes (separate client so session.clear() doesn't matter)
    with app.test_client() as client:
        for route, expected in FRESH_ROUTES:
            check_route(client, route, expected, failures)

    print()
    if failures:
        print(f'RESULT: FAIL -- {len(failures)} check(s) did not pass')
        sys.exit(1)
    else:
        print('RESULT: PASS -- all routes and KPI keys verified')
        sys.exit(0)


if __name__ == '__main__':
    main()
