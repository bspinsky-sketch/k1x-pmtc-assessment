"""
check_routes.py -- Route smoke test for the K1x PMTC Assessment.

Uses Flask's built-in test client (no running server needed). Seeds a
realistic session, hits every content route, and checks:
  1. HTTP 200 (not 302, not 500)
  2. Expected content substrings are present in the response body

Also spot-checks run_calculation() output keys.

Exit 0 = all checks pass; 1 = any failure.

NOTE: GET / always clears the session (fresh-start route) and redirects to
/profile -- checked separately as a 302, not folded into the content-route
lists below.

Rewritten 2026-08-27 -- the previous version imported a prior project's
(itsmbvf) module, session keys, and route list, none of which exist here.
See PROJECT_STATE.md Open Item #3.
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
    from app.blueprints.pmtc.calculator import run_calculation, GOAL_KEYS, CAPABILITY_KEYS, INDUSTRIES
except Exception as e:
    print(f'FAIL  Could not import calculator: {e}')
    sys.exit(1)

# ---------------------------------------------------------------------------
# Test session data -- keys must match what routes.py stores exactly
# ---------------------------------------------------------------------------
PROFILE = {
    'company': 'Acme Fund Administration',
    'industry': INDUSTRIES[0],
}
GOALS = {key: 2 for key in GOAL_KEYS}          # mid-priority on every goal
RATINGS = {key: 2 for key in CAPABILITY_KEYS}  # "Standardized" on every capability

try:
    RESULTS = run_calculation(PROFILE['company'], PROFILE['industry'], GOALS, RATINGS)
except Exception as e:
    print(f'FAIL  run_calculation() raised an exception: {e}')
    sys.exit(1)

REQUIRED_RESULT_KEYS = [
    'company', 'industry', 'your_score', 'peer_score', 'peer_count',
    'band_name', 'band_subtitle', 'narrative', 'strengths', 'gaps',
    'bar_rows', 'curve', 'capability_scores', 'strength_rank', 'gap_rank',
]

# Routes that need a pre-seeded session
SEEDED_ROUTES = [
    ('/assessment',   ['assessment']),
    ('/results',      ['your score', 'get my report']),
    ('/edit_profile', ['profile']),
]


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
    app.config['TESTING'] = True

    print('Route smoke test')
    failures = []

    # -- run_calculation() output key check
    missing_keys = [k for k in REQUIRED_RESULT_KEYS if k not in RESULTS]
    if missing_keys:
        print(f'  FAIL  run_calculation() missing result keys: {missing_keys}')
        failures.append('result_keys')
    else:
        print('  OK    run_calculation() -- all required result keys present')

    # -- GET / clears session and redirects to /profile
    with app.test_client() as client:
        resp = client.get('/')
        if resp.status_code == 302 and resp.headers.get('Location', '').endswith('/profile'):
            print('  OK    GET / -- redirects to /profile')
        else:
            print(f'  FAIL  GET / -- expected 302 to /profile, got {resp.status_code} -> {resp.headers.get("Location", "")}')
            failures.append('/')

    # -- Fresh /profile (no session needed)
    with app.test_client() as client:
        check_route(client, '/profile', ['company', 'industry'], failures)

    # -- Seeded routes (profile + goals + ratings + results all present)
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['profile'] = PROFILE
            sess['goals'] = GOALS
            sess['ratings'] = RATINGS
            sess['results'] = RESULTS
        for route, expected in SEEDED_ROUTES:
            check_route(client, route, expected, failures)

    print()
    if failures:
        print(f'RESULT: FAIL -- {len(failures)} check(s) did not pass')
        sys.exit(1)
    else:
        print('RESULT: PASS -- all routes and result keys verified')
        sys.exit(0)


if __name__ == '__main__':
    main()
