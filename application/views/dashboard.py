from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import or_

from application.models import Room

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
def index_view():
    # 读取已结束的对局记录，通过结束时间
    record = Room.query.filter(
        or_(
            Room.owner == current_user,
            Room.guest == current_user,
        ),
        Room.game_end_at.isnot(None)
    )
    # 返回所有记录
    return render_template('dashboard_index.html', record=record.all())
