import os

from flask import Flask, request

from . import db
from .routes import bp

VERSION_DEFAULT = "dev"


def create_app(test_config=None):
    app = Flask(__name__)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app.config["DATABASE"] = os.environ.get("LIFELOG_DB", os.path.join(root, "data", "lifelog.db"))
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "lifelog-dev-key")
    if test_config:
        app.config.update(test_config)

    db.init_db(app.config["DATABASE"])
    app.teardown_appcontext(db.close_db)
    app.register_blueprint(bp)

    @app.context_processor
    def build_info():
        env = os.environ.get
        return {
            "build": {
                "version": env("APP_VERSION", VERSION_DEFAULT),
                "number": env("BUILD_NUMBER", "dev"),
                "commit": env("GIT_COMMIT", "dev")[:7],
                "pod": env("HOSTNAME", "dev"),
                "frontend_pod": request.headers.get("X-Frontend-Pod", "none"),
            }
        }

    return app
