from datetime import datetime

from flask import render_template
from flask_login import current_user
from flask_socketio import join_room, close_room, leave_room
from sqlalchemy import or_

from application.extensions import db, socket
from application.models import Room, RoomInfo

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
@socket.on('lurk resource')
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


# 玩家操作
@socket.on('operation')
def operation(data):
    action = data['action']
    info = data['info']
    # 获取当前用户所在的房间信息
    room = get_room_by_current_user()

    # 取房间最近回合
    last_info = RoomInfo.query.filter_by(room_id=room.id).order_by(RoomInfo.id.desc()).first()

    if action == 'question' and (not last_info or last_info.question_user_id != current_user.id):
        # 允许提问， 上一个提问者不是自己
        room_info = RoomInfo()
        room_info.room_id = room.id
        room_info.question_user_id = current_user.id
        room_info.question = info
        db.session.add(room_info)
        db.session.commit()
        socket.emit(
            'play info',
            {
                'html': render_template('_play_info.html', msg=info),
                'action': action,
                'action_user': current_user.username,
                'action_info': info
            },
            room=room.id
        )
    #若是回答，且问题还没回答，提问者不是自己收录
    elif action == 'answer' and last_info and last_info.answer is None and last_info.question_user_id != current_user.id:
        last_info.answer = info
        last_info.answer_user_id = current_user.id
        db.session.commit()
        socket.emit('play info', {
            'html': render_template('_play_info.html', msg=info),
            'action': action,
            'action_user': current_user.username,
            'action_info': info
        }, room=room.id)

    print(room.id)


# 玩家解密对方底牌
@socket.on('over')
def over(lurk):
    room = get_room_by_current_user()
    if current_user == room.owner:
        room.owner_kill = room.owner_kill + 1
        # 猜对了
        if lurk == room.guest_lurk:
            room.victory = current_user.id
            room.game_end_at = datetime.now()
        else:
            if room.owner_kill == 3:
                # 猜错了 且是第三次猜测 则对方为胜利者
                room.victory = room.guest_id
                room.game_end_at = datetime.now()
        db.session.commit()

    elif current_user == room.guest:
        room.guest_kill = room.guest_kill + 1
        # 猜对了
        if lurk == room.owner_lurk:
            room.victory = current_user.id
            room.game_end_at = datetime.now()
        else:
            if room.guest_kill == 3:
                # 猜错了 且 是第三次猜测 则对方为胜利者
                room.victory = room.owner_kill
                room.game_end_at = datetime.now()
        db.session.commit()

    if room.victory:
        if room.victory == room.owner_id:
            wins = f'Owner: {room.owner.username}'
        else:
            wins = f'Challenger: {room.guest.username}'
        socket.emit('over success', wins, room=room.id)
        leave_room(room=room.id)
        close_room(room=room.id)
    else:
        msg = f'Player: {current_user.username} Guess Wrong,Game Continue'
        socket.emit('over fail', msg, room=room.id)
