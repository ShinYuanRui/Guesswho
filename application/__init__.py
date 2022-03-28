import click
import flask

from application.extensions import init_extensions
from application.views import init_views
from application.models import *

app = flask.Flask(__name__)
app.config.from_pyfile('settings.py')
init_extensions(app)
init_views(app)


@app.before_first_request
def before_first():
    db.create_all()


@app.cli.command("create")
@click.argument("name")
def add_user(name):
    if name == 'user':
        return create_user()


def create_user():
    username = click.prompt('admin name')
    password = click.prompt('admin password')

    if User.query.filter_by(username=username).first():
        click.echo('already exist')
    else:
        user = User()
        user.username = username
        user.role = 'admin'
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo('success')