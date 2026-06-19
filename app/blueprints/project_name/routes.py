"""
routes.py -- skeleton for [PROJECT] blueprint.
Replace [PROJECT] with project codename throughout.
"""
from flask import (render_template, request, session, redirect, url_for,
                   jsonify, make_response)
from app.blueprints.project_name import bp
from app.blueprints.project_name.calculator import run_calculation, read_defaults

# ---------------------------------------------------------------------------
# Fresh start
# ---------------------------------------------------------------------------
@bp.route('/', methods=['GET'])
def index():
    session.clear()
    return render_template('project_name/step1_profile.html', step=1)

# ---------------------------------------------------------------------------
# Edit profile (mid-flow back navigation -- preserves session)
# ---------------------------------------------------------------------------
@bp.route('/edit_profile', methods=['GET'])
def edit_profile():
    profile = session.get('profile', {})
    return render_template('project_name/step1_profile.html',
                           step=1, profile=profile)

# ---------------------------------------------------------------------------
# Profile submit
# ---------------------------------------------------------------------------
@bp.route('/step1_profile', methods=['POST'])
def step1_profile():
    revenue_raw = request.form.get('revenue', '0').replace(',', '')
    profile = {
        'company':      request.form.get('company_name', ''),
        'revenue':      float(revenue_raw),
        'employees':    int(request.form.get('employees', '0').replace(',', '')),
        'it_headcount': int(request.form.get('it_headcount', '0').replace(',', '')),
    }
    session['profile'] = profile
    session['assumption_defaults'] = read_defaults()
    session['step'] = 2
    session.modified = True
    return redirect(url_for('project_name.challenges'))

# ---------------------------------------------------------------------------
# Challenges
# ---------------------------------------------------------------------------
@bp.route('/challenges', methods=['GET'])
def challenges():
    if 'profile' not in session:
        return redirect(url_for('project_name.index'))
    return render_template('project_name/step2_challenges.html',
                           step=2, profile=session['profile'])

@bp.route('/step2_challenges', methods=['POST'])
def step2_challenges():
    if 'profile' not in session:
        return redirect(url_for('project_name.index'))
    priorities = {f'ch{i}': request.form.get(f'ch{i}', 'None') for i in range(1, 8)}
    session['priorities'] = priorities
    kpis = run_calculation(session['profile'], priorities,
                           assumptions=session.get('assumptions'))
    session['kpis'] = kpis
    session['step'] = 3
    session.modified = True
    return redirect(url_for('project_name.summary'))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
@bp.route('/summary', methods=['GET'])
def summary():
    if 'kpis' not in session:
        return redirect(url_for('project_name.index'))
    investment_defaults = session.get('investment_defaults', {})
    investment = session.get('investment', investment_defaults)
    return render_template('project_name/summary.html',
                           step=3,
                           profile=session['profile'],
                           kpis=session['kpis'],
                           priorities=session['priorities'],
                           investment=investment,
                           investment_defaults=investment_defaults,
                           assumption_defaults=session.get('assumption_defaults', {}))

# ---------------------------------------------------------------------------
# Assumptions (modal)
# ---------------------------------------------------------------------------
@bp.route('/assumptions', methods=['GET', 'POST'])
def assumptions():
    if 'profile' not in session:
        return redirect(url_for('project_name.index'))
    defaults = session.get('assumption_defaults', {})
    if request.method == 'POST':
        overrides = {k: v for k, v in request.form.items() if k != 'csrf_token'}
        session['assumptions'] = overrides
        kpis = run_calculation(session['profile'], session.get('priorities', {}),
                               assumptions=overrides)
        session['kpis'] = kpis
        session['capture_done'] = False
        session.modified = True
        return redirect(url_for('project_name.summary'))
    return render_template('project_name/assumptions.html',
                           step=3,
                           defaults=defaults,
                           assumptions=session.get('assumptions', {}))

# ---------------------------------------------------------------------------
# Calculators
# ---------------------------------------------------------------------------
@bp.route('/calculators', methods=['GET'])
def calculators():
    if 'kpis' not in session:
        return redirect(url_for('project_name.index'))
    return render_template('project_name/calculators.html',
                           step=4,
                           kpis=session['kpis'],
                           priorities=session.get('priorities', {}))

# ---------------------------------------------------------------------------
# Download report
# ---------------------------------------------------------------------------
@bp.route('/download', methods=['GET'])
def download():
    if 'kpis' not in session:
        return redirect(url_for('project_name.index'))
    from app.blueprints.project_name.report import generate_report
    investment = session.get('investment') or session.get('investment_defaults', {})
    pptx_bytes = generate_report(
        session['kpis'], session['profile'],
        session.get('priorities', {}), investment
    )
    response = make_response(pptx_bytes)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    company = session['profile'].get('company', 'Report').replace(' ', '_')
    response.headers['Content-Disposition'] = f'attachment; filename="{company}_Report.pptx"'
    return response

# ---------------------------------------------------------------------------
# Send report email
# ---------------------------------------------------------------------------
@bp.route('/send_report', methods=['POST'])
def send_report():
    if 'kpis' not in session:
        return jsonify({'error': 'No data'}), 400
    email = request.form.get('email', '').strip()
    if not email:
        return jsonify({'error': 'Email required'}), 400
    from app.blueprints.project_name.emailer import send_report_email
    investment = session.get('investment') or session.get('investment_defaults', {})
    send_report_email(email, session['profile'], session['kpis'],
                      session.get('priorities', {}), investment)
    # Data capture email backfill
    if 'profile' in session:
        try:
            from app.blueprints.project_name.data_capture import update_email
            update_email(email, session['profile'].get('company', ''))
        except Exception:
            pass
    return jsonify({'status': 'sent'})

# ---------------------------------------------------------------------------
# Investment recalculation (API)
# ---------------------------------------------------------------------------
@bp.route('/api/recalc_investment', methods=['POST'])
def recalc_investment():
    data = request.get_json(force=True) or {}
    session['investment'] = data
    session.modified = True
    return jsonify({'status': 'ok'})
