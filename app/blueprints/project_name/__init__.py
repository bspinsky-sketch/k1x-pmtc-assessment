from flask import Blueprint

bp = Blueprint('project_name', __name__,
               template_folder='../../templates/project_name',
               url_prefix='/')

from app.blueprints.project_name import routes  # noqa: F401, E402
