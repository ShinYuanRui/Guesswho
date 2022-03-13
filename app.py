import os,sys
from flask import Flask, request, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from sqlalchemy import and_, or_

name = 'Rui'

app = Flask(__name__)

# basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# SQLite URI compatible
WIN = sys.platform.startswith('win')
if WIN:
    prefix = 'sqlite:///'
else:
    prefix = 'sqlite:////'

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret string')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', prefix + os.path.join(app.root_path, 'data.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 定义ORM
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))

    def __repr__(self):
        return '<User %r>' % self.username


# 创建表格、插入数据
@app.before_first_request
def create_db():
    db.drop_all()  # 每次运行，先删除再创建
    db.create_all()

    admin = User(username='admin', password='root')
    db.session.add(admin)

    guestes = [User(username='guest1', password='guest1'),
               User(username='guest2', password='guest2'),
               User(username='guest3', password='guest3'),
               User(username='guest4', password='guest4')]
    db.session.add_all(guestes)
    db.session.commit()

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
    error = None
    if request.method == 'POST':
        if valid_login(request.form['login_user'], request.form['pswd']):
            flash("成功登录！")
            session['username'] = request.form.get('login_user')
            return redirect(url_for('index'))
        else:
            error = '错误的用户名或密码！'

    return render_template('login.html', error=error)


# 3.注销
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))


# 4.注册
@app.route('/regist', methods=['GET', 'POST'])
def regist():
    error = None
    if request.method == 'POST':
        if request.form['pswd1'] != request.form['pswd2']:
            error = '两次密码不相同！'
        elif valid_regist(request.form['register_user']):
            user = User(username=request.form['register_user'], password=request.form['pswd1'])
            db.session.add(user)
            db.session.commit()

            flash("成功注册！")
            return redirect(url_for('login'))
        else:
            error = '该用户名或邮箱已被注册！'

    return render_template('regist.html', error=error)

# @app.route('/')
# def home():
#     return render_template('home.html', name=name)
#
# @app.route('/login')
# def login():
#     return render_template('login.html', name=name)
#
@app.route('/game')
def index():
    return render_template('index.html', name=name)
#
# @app.route('/register')
# def register():
#     return render_template('regist.html', name=name)

@app.route('/user/<name>')
def user_page(name):
    return 'User: %s' % name

if __name__ == '__main__':
    app.run()