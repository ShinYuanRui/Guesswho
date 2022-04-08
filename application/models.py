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

    # 仅在赋值时候执行
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

    # 类本身cls
    # 图片存入resource文件夹中
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

    # 供数据库使用
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

    # 获得选择的best friends
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

    # 保证房间内没有选过9张图
    @property
    def resource(self):
        return json.loads(self._resource) if self._resource else None

    # 生成文件流
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

    # 就绪 可以开始游戏
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

    # 都选了才行，不可以有null
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
                # 有回合记录 且 最近的回合记录是自己主动发起的 则不能提问
                return False
            # 其他状态 均可主动提问
            # 每场对局 房主为首次发起提问人
            return True

        if current_user == self.guest:
            if self.info and self.info[-1].question_user != current_user:
                # 有回合记录 且 最近的回合记录 不是自己主动发起的 才可以提问
                return True
            # 其他状态 均不能主动提问
            # 每场对局开始 挑战者只能先接受房主的提问后 才能发起提问
            return False

    def need_answer(self):
        if self.info:
            last_room_info = self.info[-1]

            if all([
                current_user == self.owner,
                current_user != last_room_info.question_user,
                not last_room_info.answer
            ]):
                # 每个回合 最近的一次回复不是房主，，则可以回复
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
