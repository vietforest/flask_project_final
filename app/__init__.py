import os
from flask import Flask

from config import config
from .extensions import db, migrate, login_manager, csrf


def create_app(config_name=None):
    config_name = config_name or os.getenv("FLASK_CONFIG", "development")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    # make sure the instance/ folder exists (the SQLite DB goes there)
    os.makedirs(app.instance_path, exist_ok=True)

    # connect extensions to this app
    db.init_app(app)
    migrate.init_app(app, db)
    #login_manager.init_app(app)
    csrf.init_app(app)

    from . import models  # NEW: so Flask-Migrate can see the tables

    from .main import main_bp
    app.register_blueprint(main_bp)

    from .commands import register_commands  # NEW
    register_commands(app)                    # NEW

    @app.shell_context_processor              # NEW: handy objects in `flask shell`
    def shell_context():
        return {"db": db, "User": models.User,
                "Category": models.Category, "Expense": models.Expense}

    return app