from werkzeug.exceptions import Forbidden
from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_required

from application.extensions import db
from application.models import Room, Resource

bp = Blueprint('play', __name__, url_prefix='/play')


@bp.before_request
def before():
    # 资源图小于9张 则跳转至资源图片 创建游戏资源
    if Resource.query.count() < 9:
        return redirect(url_for('uploads.index_view'))


# 创建房间
@bp.route('/room/')
@login_required
def create_room_view():
    # 如果已经创建过房间 且游戏没有结束 则直接进入 防止退出丢失
    room_owner = Room.query.filter(
        Room.owner == current_user,
        Room.game_end_at.is_(None)
    ).first()
    if room_owner:
        return redirect(url_for('.entry_room_view', id=room_owner.id))

    # 如果已经进入了其他房间 且游戏没有结束 则直接进入 防止退出丢失
    room_guest = Room.query.filter(
        Room.guest == current_user,
        Room.game_end_at.is_(None)
    ).first()
    if room_guest:
        return redirect(url_for('.entry_room_view', id=room_guest.id))

    # 查找空房间 则不在创建 进入他人创建好的房间即可
    empty_room = Room.query.filter(Room.guest_id.is_(None)).first()
    if empty_room:
        return redirect(url_for('.entry_room_view', id=empty_room.id))

    # 没有创建过房间，也没有空房间 则创建一个房间
    room_owner = Room()
    room_owner.owner = current_user
    db.session.add(room_owner)
    db.session.commit()
    return redirect(url_for('.entry_room_view', id=room_owner.id))


# 进入房间
@bp.route('/room/<int:id>/')
@login_required
def entry_room_view(id):
    room = Room.query.get(id)
    if not room:
        # 当前房间不存在 转向创建房间
        return redirect(url_for('.create_room_view'))

    # 如果当前房间是自己建的 则直接进入
    if room.owner == current_user:
        return render_template('play_room.html', room=room)

    # 当前房间没有来宾 则标记进入
    if not room.guest:
        room.guest = current_user
        db.session.commit()
    else:
        # 房间有来宾，且来宾标识不是当前访问用户 则转至创建房间
        if room.guest != current_user:
            return redirect(url_for('.create_room_view'))

    return render_template('play_room.html', room=room)


@bp.route('/room/<int:id>/resource')
@login_required
def load_resource(id):
    room = Room.query.get(id)
    if current_user not in [room.owner, room.guest]:
        raise Forbidden()
    # 若两方都选择好best friends,则开始游戏
    if room.owner_lurk and room.guest_lurk:
        return redirect(url_for('.play_run', id=room.id))
    # 否则进入选择best friends 界面
    return render_template('play_resource.html', room=room)


@bp.route('/room/<int:id>/run')
@login_required
def play_run(id):
    room = Room.query.get(id)
    if current_user not in [room.owner, room.guest]:
        raise Forbidden()
    return render_template('play_run.html', room=room)
