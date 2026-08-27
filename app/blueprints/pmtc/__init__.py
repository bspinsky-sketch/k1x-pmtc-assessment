from flask import Blueprint

bp = Blueprint('pmtc', __name__,
               template_folder='../../templates/pmtc',
               url_prefix='/')

from app.blueprints.pmtc import routes  # noqa: F401, E402
