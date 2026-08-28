# Module: Authentication (Auth0)

**Status:** Complete scaffold -- verified on ITSMweb (2026-06-12)
**Library:** authlib
**Default state:** DISABLED (AUTH_REQUIRED = False). Enable per-project when login is needed.

---

## Architecture

Auth0 is wired as a Flask `before_request` hook in `app/auth.py`. Each project has a config flag:
- `AUTH_REQUIRED = False` -- all requests pass through (public tool)
- `AUTH_REQUIRED = True` -- unauthenticated requests redirected to Auth0 login

No login UI, session management, or password handling ever needs to be built from scratch.
Auth0 free tier: up to 7,500 monthly active users.

---

## One-Time Setup (when enabling auth)

### 1. Create Auth0 account

https://auth0.com -- free tier

### 2. Create Application

Applications -> Create Application -> Regular Web Application

### 3. Configure Allowed URLs

- Allowed Callback URLs: `https://[production-url]/callback`, `http://localhost:5000/callback`
- Allowed Logout URLs: `https://[production-url]`, `http://localhost:5000`

### 4. Add to .env

```
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
AUTH0_CALLBACK_URL=https://[production-url]/callback
```

---

## app/auth.py

```python
from functools import wraps
from flask import session, redirect, url_for, current_app
from authlib.integrations.flask_client import OAuth

oauth = OAuth()

def init_auth(app):
    oauth.init_app(app)
    if app.config.get('AUTH_REQUIRED'):
        oauth.register(
            name='auth0',
            client_id=app.config['AUTH0_CLIENT_ID'],
            client_secret=app.config['AUTH0_CLIENT_SECRET'],
            server_metadata_url=f"https://{app.config['AUTH0_DOMAIN']}/.well-known/openid-configuration",
            client_kwargs={'scope': 'openid profile email'},
        )

def before_request_hook():
    from flask import request
    if not current_app.config.get('AUTH_REQUIRED'):
        return  # public tool -- pass through
    excluded = ['/login', '/callback', '/logout', '/static']
    if any(request.path.startswith(e) for e in excluded):
        return
    if 'user' not in session:
        return redirect(url_for('auth.login'))

def register_auth_routes(bp):
    @bp.route('/login')
    def login():
        return oauth.auth0.authorize_redirect(redirect_uri=current_app.config['AUTH0_CALLBACK_URL'])

    @bp.route('/callback')
    def callback():
        token = oauth.auth0.authorize_access_token()
        session['user'] = token['userinfo']
        return redirect('/')

    @bp.route('/logout')
    def logout():
        session.clear()
        return redirect(f"https://{current_app.config['AUTH0_DOMAIN']}/v2/logout?returnTo={url_for('index', _external=True)}")
```

---

## Enabling Auth on a New Project

1. Set `AUTH_REQUIRED = True` in app config
2. Set AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_CALLBACK_URL in .env and hosting env vars
3. Test login/callback/logout flow locally
4. Deploy and verify on production URL

