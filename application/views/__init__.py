from . import auth, dashboard, personal, resource, play, socket


def init_views(app):
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(personal.bp)
    app.register_blueprint(resource.bp)
    app.register_blueprint(play.bp)
