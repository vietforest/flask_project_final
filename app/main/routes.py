from flask import render_template, redirect, url_for
from flask_login import login_required, current_user

from . import main_bp


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("main/index.html")


@main_bp.route("/dashboard")
@login_required          # ← like the NiceGUI middleware, but per page
def dashboard():
    return render_template("main/dashboard.html")