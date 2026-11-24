import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
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

    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    # not logged in -> JSON 401 for the API, redirect to login for pages
    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/"):
            return jsonify(error="Authentication required."), 401
        flash(login_manager.login_message, login_manager.login_message_category)
        return redirect(url_for(login_manager.login_view, next=request.full_path.rstrip("?")))

    from .commands import register_commands  # NEW
    register_commands(app)                    # NEW


        # friendly error pages (403 = not yours, 404 = doesn't exist)
    ERRORS = {
        400: ("Bad request", "The request could not be understood."),
        403: ("Not allowed", "You don't have permission to see this page."),
        404: ("Page not found", "The page or item you're looking for doesn't exist."),
        405: ("Method not allowed", "This action is not allowed here."),
    }

    def handle_error(error):
        title, message = ERRORS[error.code]
        if request.path.startswith("/api/"):          # the API always answers JSON
            return jsonify(error=title), error.code
        return render_template("errors/error.html", code=error.code,
                               title=title, message=message), error.code

    for code in ERRORS:
        app.register_error_handler(code, handle_error)

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