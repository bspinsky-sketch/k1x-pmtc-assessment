import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__, template_folder='templates')
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-me')

    # Register blueprint
    from app.blueprints.pmtc import bp as pmtc_bp
    app.register_blueprint(pmtc_bp)

    return app
