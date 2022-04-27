from datetime import datetime

from flask import render_template
from flask_login import current_user
from flask_socketio import join_room, close_room, leave_room
from sqlalchemy import or_

from application.extensions import db, socket
from application.models import Room, RoomInfo

# Statistics of online users
online_users = set()


# Get the room where the current user is located
def get_room_by_current_user():
    return Room.query.filter(
        or_(
            Room.owner == current_user,
            Room.guest == current_user,
        ),
        Room.game_end_at.is_(None)
    ).first()


# When a user links in, it will be added to the collection of online users
@socket.on('connect')
def connect():
    global online_users
    if current_user.is_authenticated:
        online_users.add(current_user.id)


# When a user disconnects, the online user collection is removed
@socket.on('disconnect')
def disconnect():
    global online_users
    if current_user.is_authenticated and current_user.id in online_users:
        online_users.remove(current_user.id)


# Join the room
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


# The player selects the picture and the system determines the friend number selected by the user
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


# Player operation
@socket.on('operation')
def operation(data):
    action = data['action']
    info = data['info']
    # Get the room information of the current user
    room = get_room_by_current_user()

    # Take the latest round of room
    last_info = RoomInfo.query.filter_by(room_id=room.id).order_by(RoomInfo.id.desc()).first()

    if action == 'question' and (not last_info or last_info.question_user_id != current_user.id):
        # The last questioner is not himself and is allowed to ask questions
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
    # If the answer link, and the question has not been answered, the questioner is not included by himself
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


# Players decrypt each other's friends
@socket.on('over')
def over(lurk):
    room = get_room_by_current_user()
    if current_user == room.owner:
        room.owner_kill = room.owner_kill + 1
        # Guess right
        if lurk == room.guest_lurk:
            room.victory = current_user.id
            room.game_end_at = datetime.now()
        else:
            if room.owner_kill == 3:
                # If the guess is wrong and it is the third guess, the other party is the winner
                room.victory = room.guest_id
                room.game_end_at = datetime.now()
        db.session.commit()

    elif current_user == room.guest:
        room.guest_kill = room.guest_kill + 1
        # Guess right
        if lurk == room.owner_lurk:
            room.victory = current_user.id
            room.game_end_at = datetime.now()
        else:
            if room.guest_kill == 3:
                # If the guess is wrong and it is the third guess, the other party is the winner
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
