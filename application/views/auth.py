import bdb

from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user

from application.extensions import db
from application.forms import LoginForm, RegisterForm
from application.models import User


bp = Blueprint('auth', __name__)


@bp.route('/reg', methods=['GET', 'POST'])
def reg():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index_view'))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if not user:
            user = User()
            user.username = form.username.data
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('.login'))
        else:
            flash('This account is existed already', 'error')
    return render_template('auth_reg.html', form=form)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index_view'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.verify_password(form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect(url_for('dashboard.index_view'))
        else:
            flash('Wrong password', 'error')
    return render_template('auth_login.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('.login'))
