from werkzeug.exceptions import Forbidden
from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_required

from application.extensions import db
from application.models import Room, Resource

bp = Blueprint('play', __name__, url_prefix='/play')


@bp.before_request
def before():
    # If the resource map is less than 9, jump to the resource picture to create game resources
    if Resource.query.count() < 9:
        return redirect(url_for('resource.index_view'))


# Create room
@bp.route('/room/')
@login_required
def create_room_view():
    # If a room has been created and the game is not over, enter directly to prevent loss of exit
    room_owner = Room.query.filter(
        Room.owner == current_user,
        Room.game_end_at.is_(None)
    ).first()
    if room_owner:
        return redirect(url_for('.entry_room_view', id=room_owner.id))

    # If you have entered other rooms and the game is not over, enter directly to prevent loss of exit
    room_guest = Room.query.filter(
        Room.guest == current_user,
        Room.game_end_at.is_(None)
    ).first()
    if room_guest:
        return redirect(url_for('.entry_room_view', id=room_guest.id))

    # If you find an empty room, you don't need to enter the room created by others
    empty_room = Room.query.filter(Room.guest_id.is_(None)).first()
    if empty_room:
        return redirect(url_for('.entry_room_view', id=empty_room.id))

    # No room was created and none was empty
    room_owner = Room()
    room_owner.owner = current_user
    db.session.add(room_owner)
    db.session.commit()
    return redirect(url_for('.entry_room_view', id=room_owner.id))


# get into the room
@bp.route('/room/<int:id>/')
@login_required
def entry_room_view(id):
    room = Room.query.get(id)
    if not room:
        # The current room does not exist. Turn to create a room
        return redirect(url_for('.create_room_view'))

    # If the current room is built by yourself, you can enter directly
    if room.owner == current_user:
        return render_template('play_room.html', room=room)

    # Mark entry if there are no guests in the current room
    if not room.guest:
        room.guest = current_user
        db.session.commit()
    else:
        # If the room has guests and the guest ID is not the current user, go to create the room
        if room.guest != current_user:
            return redirect(url_for('.create_room_view'))

    return render_template('play_room.html', room=room)


@bp.route('/room/<int:id>/resource')
@login_required
def load_resource(id):
    room = Room.query.get(id)
    if current_user not in [room.owner, room.guest]:
        raise Forbidden()
    # If both parties choose best friends, start the game
    if room.owner_lurk and room.guest_lurk:
        return redirect(url_for('.play_run', id=room.id))
    # Otherwise, enter the interface of selecting best friends
    return render_template('play_resource.html', room=room)


@bp.route('/room/<int:id>/run')
@login_required
def play_run(id):
    room = Room.query.get(id)
    if current_user not in [room.owner, room.guest]:
        raise Forbidden()
    return render_template('play_run.html', room=room)
