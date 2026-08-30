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
from app.blueprints.pmtc import data_capture
from app.blueprints.pmtc import emailer


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
        # Lets the breadcrumb link forward to Results once it's already
        # been computed (e.g. user came back to Profile via "Back" from
        # Assessment/Results to tweak something, without losing the ability
        # to jump straight back to Results if they don't actually resubmit).
        results_done=bool(session.get('results')),
    )


# Back-navigation alias used by the assessment/results pages' "Back" links —
# same view as /profile, prefilled from whatever is already in session.
@bp.route('/edit_profile', methods=['GET'])
def edit_profile():
    return profile_page()


@bp.route('/profile', methods=['POST'])
def profile_submit():
    # No fabricated fallback text here on purpose (this used to silently
    # substitute 'Company XYZ' / INDUSTRIES[0] for a blank submission) -- the
    # profile page's own JS blocks submission until both fields are actually
    # filled in, same gate it already uses for the goal sliders, so this path
    # is only reached with a genuinely blank value if that JS is bypassed
    # (disabled JS, a direct POST). In that case, store what was actually
    # submitted rather than lying with placeholder data that would otherwise
    # end up in the report and the Google Sheet capture.
    profile = {
        'company': (request.form.get('company') or '').strip(),
        'industry': request.form.get('industry') or '',
    }
    if profile['industry'] not in INDUSTRIES:
        profile['industry'] = ''

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
    return render_template(
        'pmtc/assessment.html',
        ratings=session.get('ratings'),
        # Same idea as profile_page(): breadcrumb should link forward to
        # Results if they're already computed for this session.
        results_done=bool(session.get('results')),
    )


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

    # Data capture (Phase 10): write/update the assessment portion of this
    # session's Sheet row. First time through, row_number is None and
    # capture_result() appends a new row; if the user later goes back,
    # revises an answer, and resubmits, capture_row is already set and this
    # updates that same row's assessment columns in place rather than
    # appending a second one -- see data_capture.py's module docstring.
    row_number = data_capture.capture_result(
        profile['company'], profile['industry'], goals, session['results'],
        row_number=session.get('capture_row'),
    )
    if row_number:
        session['capture_row'] = row_number

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
# Backfills First Name/Last Name/Email/Opt-In into the Sheet row this
# session already wrote at assessment-submit time (session['capture_row']).
# Defensive fallback: if capture_row was never set (e.g. Sheets was
# unreachable when the assessment was submitted), retry capture_result()
# once here so the lead isn't silently lost, before writing the lead
# columns into whatever row that produces.
@bp.route('/api/lead', methods=['POST'])
def lead_capture():
    data = request.get_json(silent=True) or {}
    lead = {
        'first_name': data.get('first_name', ''),
        'last_name': data.get('last_name', ''),
        'company': data.get('company', ''),
        'email': data.get('email', ''),
        'opt_in': bool(data.get('opt_in')),
    }
    session['lead'] = lead
    session.modified = True

    row_number = session.get('capture_row')
    if not row_number and 'profile' in session and 'results' in session:
        profile = session['profile']
        row_number = data_capture.capture_result(
            profile['company'], profile['industry'],
            session.get('goals', {}), session['results'],
        )
        if row_number:
            session['capture_row'] = row_number
            session.modified = True

    data_capture.update_lead_info(
        row_number, lead['first_name'], lead['last_name'], lead['email'], lead['opt_in'],
    )
    # The report itself. Fired after the lead is recorded, never before: the
    # Sheet is the durable record and the mail is not, so if only one of the
    # two can happen it has to be the Sheet. The call is asynchronous inside
    # emailer.py, so it costs this request milliseconds rather than the minute
    # the PDF conversion takes -- see emailer.py's module docstring.
    #
    # session['results'] is passed whole rather than picked apart, so that
    # adding a figure to the report later is a change in the mailer only.
    # session['goals'] goes along too -- not part of run_calculation()'s own
    # return, but needed once the mailer renders the real Output Report
    # templates (Open Item #2/#17), whose page 2 needs the visitor's actual
    # goal priorities, not just the computed results.
    emailer.send_report(session.get('results') or {}, lead, session.get('goals') or {})

    # 'received' is about the lead, and it is honest about it: the modal has
    # already promised a report, and by design nothing here waits long enough
    # to know whether one was sent.
    return jsonify({'status': 'received'})
