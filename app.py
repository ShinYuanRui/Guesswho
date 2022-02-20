from flask import url_for, Flask, render_template

app = Flask(__name__)

name = 'Rui'

@app.route('/')
def login():
    return render_template('login.html', name=name)

@app.route('/game')
def index():
    return render_template('index.html', name=name)

@app.route('/register')
def register():
    return render_template('register.html', name=name)

@app.route('/user/<name>')
def user_page(name):
    return 'User: %s' % name


if __name__ == '__main__':
    app.run()
