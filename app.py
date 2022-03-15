import os
import sys

try:
    from urlparse import urlparse, urljoin
except ImportError:
    from urllib.parse import urlparse, urljoin

from flask import Flask, request, render_template, redirect, url_for, flash, session
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from sqlalchemy import and_
from flask_login import UserMixin, LoginManager
from flask_dropzone import Dropzone, random_filename
from flask_login import login_user, current_user
# , logout_user, login_required,
from werkzeug.security import generate_password_hash, check_password_hash

from forms import LoginForm

name = 'Rui'

app = Flask(__name__)
# basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
bootstrap = Bootstrap(app)
# SQLite URI compatible
WIN = sys.platform.startswith('win')
if WIN:
    prefix = 'sqlite:///'
else:
    prefix = 'sqlite:////'

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret string')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', prefix + os.path.join(app.root_path, 'data.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_PATH'] = os.path.join(app.root_path, 'uploads')

if not os.path.exists(app.config['UPLOAD_PATH']):
    os.makedirs(app.config['UPLOAD_PATH'])

db = SQLAlchemy(app)
# Flask-Dropzone config
app.config['UPLOAD_IMAGE_TYPE'] = ['JPG', 'GIF', 'PNG', 'png', 'jpg', 'gif', 'JPEG', 'jpeg']
app.config['DROPZONE_MAX_FILE_SIZE'] = 3
app.config['DROPZONE_MAX_FILES'] = 1
dropzone = Dropzone(app)


# 定义ORM
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password_hash = db.Column(db.String(128))

    # avatar = db.Column(db.String(80))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)


login_manager = LoginManager(app)


@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    return user


login_manager.login_view = 'login'
# login_manager.login_message = 'Your custom message'
login_manager.login_message_category = 'warning'


# # 创建表格、插入数据
# @app.before_first_request
# def create_db():
#     db.drop_all()  # 每次运行，先删除再创建
#     db.create_all()
#
#     # admin = User(username='admin', password='root')
#     # db.session.add(admin)
#     #
#     # guestes = [User(username='sun', password='123'),
#     #            User(username='wei', password='123'),
#     #            User(username='rui', password='123'),
#     #            User(username='guest', password='guest')]
#     # db.session.add_all(guestes)
#     db.session.commit()

############################################
# 辅助函数、装饰器
############################################


# 登录检验（用户名、密码验证）
def valid_login(username, password):
    user = User.query.filter(and_(User.username == username, User.password == password)).first()
    if user:
        return True
    else:
        return False


# 注册检验（用户名、邮箱验证）
def valid_regist(username):
    user = User.query.filter(User.username == username).first()
    if user:
        return False
    else:
        return True


# 登录
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # if g.user:
        if session.get('username'):
            return func(*args, **kwargs)
        else:
            return redirect(url_for('login', next=request.url))

    return wrapper


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['UPLOAD_IMAGE_TYPE']




############################################
# 路由
############################################

# 1.主页
@app.route('/')
def home():
    return render_template('home.html', name=name)


# 2.登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('panel'))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember = form.remember.data
        user = User.query.first()
        if user:
            if username == user.username and user.validate_password(password):
                login_user(user, remember)
                flash('Welcome back.', 'info')
                return redirect(url_for('panel'))
            flash('Invalid username or password.', 'warning')
        else:
            flash('No account.', 'warning')
    return render_template('login.html', form=form)
    # error = None
    # if request.method == 'POST':
    #     if valid_login(request.form['login_user'], request.form['pswd']):
    #         flash("成功登录！")
    #         session['username'] = request.form.get('login_user')
    #         return redirect(url_for('panel'))
    #     else:
    #         error = '错误的用户名或密码！'
    #
    # return render_template('login.html', error=error)


# 3.注销
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

    # form = RegisterForm()
    # if form.validate_on_submit():
    #     name = form.name.data
    #     email = form.email.data.lower()
    #     username = form.username.data
    #     password = form.password.data
    #     user = User(name=name, email=email, username=username)
    #     user.set_password(password)
    #     db.session.add(user)
    #     db.session.commit()
    #     token = generate_token(user=user, operation='confirm')
    #     send_confirm_email(user=user, token=token)
    #     flash('Confirm email sent, check your inbox.', 'info')
    #     return redirect(url_for('.login'))
    # return render_template('auth/register.html', form=form)


# 4.注册
@app.route('/regist', methods=['GET', 'POST'])
def regist():
    error = None
    if request.method == 'POST':
        if request.form['pswd1'] != request.form['pswd2']:
            error = '两次密码不相同！'
        elif valid_regist(request.form['register_user']):
            user = User(username=request.form['register_user'],
                        password_hash=generate_password_hash(request.form['pswd1']))
            db.session.add(user)
            db.session.commit()

            flash("成功注册！")
            return redirect(url_for('login'))
        else:
            error = '该用户名或邮箱已被注册！'

    return render_template('regist.html', error=error)


@app.route('/center')
def panel():
    return render_template("panel.html")


# @app.route('/upimage', methods=['GET', 'POST'])
# def upload():
#     if request.method == 'POST':
#         f = request.files.get('file')  # 获取文件对象
#
#         # 创建文件夹
#         basefile = os.path.join(os.path.abspath('uploads'), 'avatars')
#         if not os.path.exists(basefile):
#             os.mkdir(basefile)
#
#         # 验证后缀
#         ext = os.path.splitext(f.filename)[1]
#         if ext.split('.')[-1] not in UPLOAD_IMAGE_TYPE:
#             return 'Image only!', 400
#
#         # 生成文件名　　使用uuid模块
#         filename = request.form['register_user']
#         path = os.path.join(basefile, filename)
#         f.save(path)
#     return render_template('upload.html')

# @app.route('/uploads/<path:filename>')
# def get_file(filename):
#     return send_from_directory(app.config['UPLOAD_PATH'], filename)

@app.route('/game')
def index():
    return render_template('index.html', username=session.get('username'))


@app.route('/dropzone-upload', methods=['GET', 'POST'])
def dropzone_upload():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            return 'This field is required.', 400
        f = request.files.get('file')

        if f and allowed_file(f.filename):
            filename = random_filename(f.filename)
            f.save(os.path.join(
                app.config['UPLOAD_PATH'], filename
            ))
        else:
            return 'Invalid file type.', 400
    return render_template('dropzone.html')


@app.route('/user/<name>')
def user_page(name):
    return 'User: %s' % name


if __name__ == '__main__':
    app.run()
