import os
from flask import Flask
from datetime import date
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
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"           # NEW: where @login_required redirects
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"
    csrf.init_app(app)

    from . import models  # NEW: so Flask-Migrate can see the tables

    from .main import main_bp
    app.register_blueprint(main_bp)

    from .auth import auth_bp                         # NEW
    app.register_blueprint(auth_bp, url_prefix="/auth")

    from .commands import register_commands  # NEW
    register_commands(app)                    # NEW

    @app.shell_context_processor              # NEW: handy objects in `flask shell`
    def shell_context():
        return {"db": db, "User": models.User,
                "Category": models.Category, "Expense": models.Expense}

    
# {{ value|money }} in templates -> "€1,284.50"
    @app.template_filter("money")
    def money(value, decimals=2):
        value = float(value or 0)
        sign = "-" if value < 0 else ""
        return f"{sign}{app.config['CURRENCY']}{abs(value):,.{decimals}f}"

    # variables available in every template
    @app.context_processor
    def inject_globals():
        return {"today": date.today()}

    return app