import os

from flask import Flask, request

from . import db


def create_app(test_config=None):
    app = Flask(__name__)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app.config["DATABASE"] = os.environ.get("LIFELOG_DB", os.path.join(root, "data", "lifelog.db"))
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "lifelog-dev-key")
    app.config["CURRENCY"] = os.environ.get("CURRENCY", "₹")
    app.config["SEED"] = os.environ.get("LIFELOG_SEED", "1") == "1"
    if test_config:
        app.config.update(test_config)

    db.init_db(app.config["DATABASE"], seed=app.config["SEED"])
    app.teardown_appcontext(db.close_db)

    from .service import num
    app.jinja_env.filters["num"] = num

    from .api import bp as api_bp
    from .goals import bp as goals_bp
    from .insights import bp as insights_bp
    from .trackers import bp as trackers_bp
    from .views import bp as views_bp

    for blueprint in (views_bp, trackers_bp, insights_bp, goals_bp, api_bp):
        app.register_blueprint(blueprint)

    @app.context_processor
    def build_info():
        env = os.environ.get
        return {
            "currency": app.config["CURRENCY"],
            "build": {
                "version": env("APP_VERSION", "dev"),
                "number": env("BUILD_NUMBER", "dev"),
                "commit": env("GIT_COMMIT", "dev")[:7],
                "pod": env("HOSTNAME", "dev"),
                "frontend_pod": request.headers.get("X-Frontend-Pod", "none"),
            },
        }

    return app
