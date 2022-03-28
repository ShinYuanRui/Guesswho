from datetime import datetime

from flask import render_template
from flask_login import current_user
from flask_socketio import join_room, close_room, leave_room
from sqlalchemy import or_

from application.extensions import db, socket
from application.models import Room

# 统计在线用户
online_users = set()


# 获取当前用户所在的房间
def get_room_by_current_user():
    return Room.query.filter(
        or_(
            Room.owner == current_user,
            Room.guest == current_user,
        ),
        Room.game_end_at.is_(None)
    ).first()


# 当有用户链接进来 则加入在线用户的集合
@socket.on('connect')
def connect():
    global online_users
    if current_user.is_authenticated:
        online_users.add(current_user.id)


# 当有用户断开链接 则移除在线用户集合
@socket.on('disconnect')
def disconnect():
    global online_users
    if current_user.is_authenticated and current_user.id in online_users:
        online_users.remove(current_user.id)


# 加入房间
@socket.on('join room')
def on_join():
    room = get_room_by_current_user()
    join_room(room.id)
    if not room.resource:
        room.generate_resource()
        room.game_start_at = datetime.now()
        db.session.commit()
    if room.owner and room.guest:
        socket.emit('play load', room=room.id)


# 玩家选中的图片，来自play_resource选择后连接来，并确定用户选择的friend号
@socket.on('lurk uploads')
def lurk_resource(resource_id):
    room = get_room_by_current_user()
    if int(resource_id) in [int(item['id']) for item in room.resource]:
        if current_user == room.owner and not room.owner_lurk:
            room.owner_lurk = resource_id
            db.session.commit()
        elif current_user == room.guest and not room.guest_lurk:
            room.guest_lurk = resource_id
            db.session.commit()

    if room.owner_lurk and room.guest_lurk:
        socket.emit('play run', room=room.id)


