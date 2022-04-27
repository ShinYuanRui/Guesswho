import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.datastructures import FileStorage
from flask import current_app, url_for
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql.expression import func
from flask_login import UserMixin, current_user
from application.extensions import db, login_manager


class User(UserMixin, db.Model):
    id = Column(Integer, primary_key=True)
    username = Column(String(128), nullable=False, unique=True)
    nickname = Column(String(128), default='', comment='nickname')
    _avatar = Column(
        'avatar',
        String(64),
        default='avatar/_default.jpg',
        comment='avatar'
    )
    role = db.Column(db.Enum('admin', 'simpleuser'), nullable=False, default='simpleuser')
    password = Column(String(128), nullable=False)

    @property
    def avatar(self):
        return url_for('static', filename=self._avatar)

    # Execute only at assignment time
    @avatar.setter
    def avatar(self, file):
        if file and isinstance(file, FileStorage):
            ext_name = file.headers['Content-Type'].split('/')[1]
            avatar_name = f'avatar/{self.username}.{ext_name}'
            file.save(Path(current_app.static_folder) / avatar_name)
            self._avatar = avatar_name

    @staticmethod
    @login_manager.user_loader
    def loader_user(user_id):
        return User.query.get(user_id)

    def set_password(self, value):
        self.password = generate_password_hash(value)

    def verify_password(self, value):
        return check_password_hash(self.password, value)


class Resource(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True)

    @property
    def url(self):
        return url_for('static', filename=self.name)

    # #Save the pictures in the resource folder
    @classmethod
    def set_file(cls, file):
        if file and isinstance(file, FileStorage):
            ext_name = file.headers['Content-Type'].split('/')[1]
            file_name = f'resource/{uuid4()}.{ext_name}'
            file.save(Path(current_app.static_folder) / file_name)
            obj = cls(name=file_name)
            db.session.add(obj)
            db.session.commit()
            return obj


class Room(db.Model):
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('user.id'), index=True)
    guest_id = Column(Integer, ForeignKey('user.id'), index=True)

    # For database use
    _resource = Column('resource', JSON)

    owner_lurk = Column(Integer)
    guest_lurk = Column(Integer)

    owner = db.relationship('User', foreign_keys=owner_id)
    guest = db.relationship('User', foreign_keys=guest_id)

    info = db.relationship('RoomInfo', back_populates='room')

    create_at = db.Column(DateTime, comment='At Start', default=datetime.now)
    game_start_at = Column(DateTime, comment='Start time')
    game_end_at = Column(DateTime, comment='End time')
    victory = db.Column(Integer, comment='Winner')

    owner_kill = db.Column(Integer, nullable=False, default=0)
    guest_kill = db.Column(Integer, nullable=False, default=0)

    # Get the best friends of user's choice
    @property
    def owner_lurk_src(self):
        for target in self.resource:
            if int(target['id']) == self.owner_lurk:
                return url_for('static', filename=target['name'])

    @property
    def guest_lurk_src(self):
        for target in self.resource:
            if int(target['id']) == self.guest_lurk:
                return url_for('static', filename=target['name'])

    # Ensure that no 9 pictures have been selected in the room
    @property
    def resource(self):
        return json.loads(self._resource) if self._resource else None

    # Generate file stream
    def generate_resource(self):
        resource = Resource.query.order_by(func.random()).limit(9)
        self._resource = json.dumps(
            [
                {
                    'id': target.id,
                    'name': target.name,
                    'url': target.url
                } for target in resource
            ]
        )

    # Ready to start the game
    def can_ready(self):
        if all([
            self.owner,
            self.guest,
            self.owner == current_user,
            not self.resource,
            not self.game_start_at,
        ]):
            return True
        return False

    # must both choose，no null
    def can_resource(self):
        if all([
            self.resource,
            not self.owner_lurk or not self.guest_lurk
        ]):
            return True
        return False

    def can_question(self):
        if current_user == self.owner:
            if self.info and self.info[-1].question_user == current_user:
                # If there is a round record and the most recent round record is initiated by yourself, you can't ask
                # questions
                return False
            # Other states can take the initiative to ask questions
            # The owner of each game is the first initiator to ask questions
            return True

        if current_user == self.guest:
            if self.info and self.info[-1].question_user != current_user:
                # You can only ask questions if you have a round record and the most recent round record is not
                # initiated by yourself
                return True
            # You can't take the initiative to ask questions in other states
            # At the beginning of each game, the challenger can only ask questions after
            # accepting the questions of the owner
            return False

    def need_answer(self):
        if self.info:
            last_room_info = self.info[-1]

            if all([
                current_user == self.owner,
                current_user != last_room_info.question_user,
                not last_room_info.answer
            ]):
                # If the last reply of each round is not the owner, you can reply
                return True

            if all([
                current_user == self.guest,
                current_user != last_room_info.question_user,
                not last_room_info.answer
            ]):
                return True

        return False


class RoomInfo(db.Model):
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey('room.id'), index=True)
    question_at = Column(DateTime, default=datetime.now)
    question = Column(Text, nullable=False)
    answer = Column(String(128))
    answer_at = Column(DateTime, onupdate=datetime.now)
    question_user_id = Column(Integer, ForeignKey('user.id'), index=True)
    answer_user_id = Column(Integer, ForeignKey('user.id'), index=True)

    room = db.relationship('Room', back_populates='info')

    question_user = db.relationship('User', foreign_keys=question_user_id)
    answer_user = db.relationship('User', foreign_keys=answer_user_id)
