from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_bootstrap import Bootstrap5
from flask_dropzone import Dropzone


csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please login'
db = SQLAlchemy()
socket = SocketIO()
bootstrap = Bootstrap5()
dropzone = Dropzone()


def init_extensions(app):
    csrf.init_app(app)
    login_manager.init_app(app)
    db.init_app(app)
    socket.init_app(app)
    bootstrap.init_app(app)
    dropzone.init_app(app)
