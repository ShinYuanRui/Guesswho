from flask import Blueprint, render_template, flash
from flask_login import current_user, login_required

from application.forms import PersonalActionForm
from application.extensions import db

bp = Blueprint('personal', __name__, url_prefix='/personal')


@bp.route('/', methods=['GET', 'POST'])
@login_required
def index_view():
    form = PersonalActionForm(obj=current_user)
    if form.validate_on_submit():
        current_user.avatar = form.avatar.data
        current_user.nickname = form.nickname.data
        db.session.commit()
        flash('Success', 'success')
    return render_template('personal_index.html', form=form)
