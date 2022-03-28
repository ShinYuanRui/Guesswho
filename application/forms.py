from flask_wtf import FlaskForm
from wtforms import fields, validators


class LoginForm(FlaskForm):
    username = fields.StringField('Username', validators=[validators.data_required()])
    password = fields.PasswordField('Password', validators=[validators.data_required()])
    remember = fields.BooleanField('Remember')
    submit = fields.SubmitField('Login')


class RegisterForm(FlaskForm):
    username = fields.StringField('Username', validators=[validators.data_required()])
    password = fields.PasswordField('Password', validators=[validators.data_required()])
    submit = fields.SubmitField('Register')


class PersonalActionForm(FlaskForm):
    username = fields.StringField('Username')
    nickname = fields.StringField('Nickname')
    avatar = fields.FileField('Avatar')
