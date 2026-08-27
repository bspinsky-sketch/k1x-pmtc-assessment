import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__, template_folder='templates')
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-me')
    app.config['AUTH_REQUIRED'] = os.environ.get('AUTH_REQUIRED', 'False').lower() == 'true'
    app.config['AUTH0_DOMAIN'] = os.environ.get('AUTH0_DOMAIN', '')
    app.config['AUTH0_CLIENT_ID'] = os.environ.get('AUTH0_CLIENT_ID', '')
    app.config['AUTH0_CLIENT_SECRET'] = os.environ.get('AUTH0_CLIENT_SECRET', '')
    app.config['AUTH0_CALLBACK_URL'] = os.environ.get('AUTH0_CALLBACK_URL', '')

    # Register blueprint
    from app.blueprints.pmtc import bp as pmtc_bp
    app.register_blueprint(pmtc_bp)

    # Auth middleware
    from app.auth import before_request_hook
    app.before_request(before_request_hook)

    return app
