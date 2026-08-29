import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__, template_folder='templates')
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-me')

    # Cookie settings for the iframe embed. The tool is loaded in an iframe on
    # a K1x-hosted page, which is cross-site: a SameSite=Lax cookie (Flask's
    # effective default) is not sent in that context, so the session would be
    # lost between every step of the wizard. SameSite=None fixes that, and
    # browsers reject SameSite=None unless Secure is also set.
    #
    # Both are read from the environment with secure production defaults so
    # that local development can opt out: Secure means HTTPS-only, and a local
    # dev server on http://127.0.0.1:5000 would otherwise silently stop
    # setting the session cookie at all.
    app.config.update(
        SESSION_COOKIE_SAMESITE=os.environ.get('SESSION_COOKIE_SAMESITE', 'None'),
        SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', 'true').lower() == 'true',
    )

    # Register blueprint
    from app.blueprints.pmtc import bp as pmtc_bp
    app.register_blueprint(pmtc_bp)

    return app
