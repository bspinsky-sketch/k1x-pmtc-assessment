"""
routes.py -- K1x PMTC Assessment blueprint.

Flow: Profile -> Assessment -> Results, per the routing plan Ben confirmed
("routing plan looks good"). Session-based multi-step wizard, following
PLATFORM.md's pattern: GET / always clears the session; edit views prefill
from whatever is already in session; session.modified = True is set after
any in-place mutation of a session dict.
"""
from flask import render_template, request, session, redirect, url_for, jsonify
from app.blueprints.pmtc import bp
from app.blueprints.pmtc.calculator import (
    run_calculation, GOAL_KEYS, CAPABILITY_KEYS, INDUSTRIES,
)


def _int_or_zero(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# Fresh start
# ---------------------------------------------------------------------------
@bp.route('/', methods=['GET'])
def index():
    session.clear()
    return redirect(url_for('pmtc.profile_page'))


# ---------------------------------------------------------------------------
# Profile (step 1)
# ---------------------------------------------------------------------------
@bp.route('/profile', methods=['GET'])
def profile_page():
    return render_template(
        'pmtc/profile.html',
        profile=session.get('profile'),
        goals=session.get('goals'),
    )


# Back-navigation alias used by the assessment/results pages' "Back" links —
# same view as /profile, prefilled from whatever is already in session.
@bp.route('/edit_profile', methods=['GET'])
def edit_profile():
    return profile_page()


@bp.route('/profile', methods=['POST'])
def profile_submit():
    profile = {
        'company': (request.form.get('company') or 'Company XYZ').strip(),
        'industry': request.form.get('industry') or INDUSTRIES[0],
    }
    if profile['industry'] not in INDUSTRIES:
        profile['industry'] = INDUSTRIES[0]

    goals = {key: _int_or_zero(request.form.get('goal_' + key)) for key in GOAL_KEYS}
    goals = {key: max(0, min(4, value)) for key, value in goals.items()}

    session['profile'] = profile
    session['goals'] = goals
    # A profile re-submit invalidates any previously computed results — the
    # user has to re-run the assessment (or their existing ratings carry
    # forward unchanged, but the derived results are stale either way).
    session.pop('results', None)
    session.modified = True
    return redirect(url_for('pmtc.assessment_page'))


# ---------------------------------------------------------------------------
# Assessment (step 2)
# ---------------------------------------------------------------------------
@bp.route('/assessment', methods=['GET'])
def assessment_page():
    if 'profile' not in session:
        return redirect(url_for('pmtc.profile_page'))
    return render_template('pmtc/assessment.html', ratings=session.get('ratings'))


@bp.route('/assessment', methods=['POST'])
def assessment_submit():
    if 'profile' not in session:
        return redirect(url_for('pmtc.profile_page'))

    ratings = {key: _int_or_zero(request.form.get('rating_' + key)) for key in CAPABILITY_KEYS}
    ratings = {key: max(0, min(5, value)) for key, value in ratings.items()}
    session['ratings'] = ratings

    profile = session['profile']
    goals = session.get('goals', {key: 0 for key in GOAL_KEYS})
    session['results'] = run_calculation(profile['company'], profile['industry'], goals, ratings)
    session.modified = True
    return redirect(url_for('pmtc.results_page'))


# ---------------------------------------------------------------------------
# Results (step 3)
# ---------------------------------------------------------------------------
@bp.route('/results', methods=['GET'])
def results_page():
    if 'results' not in session:
        return redirect(url_for('pmtc.profile_page'))
    return render_template('pmtc/results.html', results=session['results'])


# ---------------------------------------------------------------------------
# Lead capture (the Results page's "Get My Report" modal)
# ---------------------------------------------------------------------------
# Best-effort stub: accepts the submission and returns success so the modal
# always shows its confirmation state, but does not yet persist the lead
# anywhere. The data-capture method (Google Sheets vs. something else) and
# the report-email delivery method are both unconfirmed defaults in
# PROJECT_STATE.md (Q2/Q3) -- wire this up to app/blueprints/pmtc/data_capture.py
# and emailer.py once Ben confirms those.
@bp.route('/api/lead', methods=['POST'])
def lead_capture():
    data = request.get_json(silent=True) or {}
    session['lead'] = {
        'first_name': data.get('first_name', ''),
        'last_name': data.get('last_name', ''),
        'company': data.get('company', ''),
        'email': data.get('email', ''),
        'opt_in': bool(data.get('opt_in')),
    }
    session.modified = True
    return jsonify({'status': 'received'})
