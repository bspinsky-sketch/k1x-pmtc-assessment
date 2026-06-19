"""
Auth0 middleware scaffold.
Set AUTH_REQUIRED=True in app config to enable login enforcement.
Default: AUTH_REQUIRED=False (all requests pass through).
"""
from flask import session, redirect, url_for, request, current_app

def before_request_hook():
    if not current_app.config.get('AUTH_REQUIRED'):
        return  # public tool -- pass through

    excluded = ['/login', '/callback', '/logout', '/static']
    if any(request.path.startswith(e) for e in excluded):
        return

    if 'user' not in session:
        return redirect(url_for('auth.login'))
