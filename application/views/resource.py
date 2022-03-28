from werkzeug.exceptions import Forbidden
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from application.models import Resource
from application.extensions import csrf

bp = Blueprint('uploads', __name__, url_prefix='/uploads')


@bp.before_request
def before():
    if current_user.role != 'admin':
        raise Forbidden()


@bp.route('/')
@login_required
def index_view():
    result = Resource.query.order_by(Resource.id.desc()).all()
    return render_template('resource_index.html', resource=result)


@bp.post('/upload/')
@login_required
@csrf.exempt
def upload_view():
    if request.method == 'POST':
        Resource.set_file(request.files.get('file'))
    return 'success'
