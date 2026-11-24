from datetime import date, timedelta

from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func

from . import main_bp
from ..extensions import db
from ..models import Expense, Category


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("main/index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    today = date.today()
    first_day = today.replace(day=1)
    next_month = (first_day + timedelta(days=32)).replace(day=1)
    days_in_month = (next_month - first_day).days

    # only MY expenses of THIS month
    this_month = (
        Expense.user_id == current_user.id,
        Expense.date >= first_day,
        Expense.date < next_month,
    )

    # --- stat cards ---
    spent = float(db.session.query(func.coalesce(func.sum(Expense.amount), 0))
                  .filter(*this_month).scalar())
    budget = float(current_user.monthly_budget)
    left = budget - spent
    percent = min(round(spent / budget * 100), 100) if budget else 0
    days_passed = today.day
    days_left = days_in_month - today.day
    daily_avg = spent / days_passed
    per_day_left = (left / days_left) if days_left > 0 and left > 0 else 0

    # --- "By category" donut ---
    rows = (db.session.query(Category, func.sum(Expense.amount).label("total"))
            .join(Expense, Expense.category_id == Category.id)
            .filter(*this_month)
            .group_by(Category.id)
            .order_by(func.sum(Expense.amount).desc())
            .all())
    by_category = [(cat, float(total)) for cat, total in rows]

    # build a CSS conic-gradient like "#f59f00 0% 32%, #206bc4 32% 50%, ..."
    stops, start = [], 0.0
    for cat, total in by_category:
        end = start + (total / spent * 100 if spent else 0)
        stops.append(f"{cat.color} {start:.2f}% {end:.2f}%")
        start = end
    donut_gradient = f"conic-gradient({', '.join(stops)})" if stops else "none"

    # --- "Daily spending" bars: one value per day, from the 1st to today ---
    daily_rows = (db.session.query(Expense.date, func.sum(Expense.amount))
                  .filter(*this_month)
                  .group_by(Expense.date)
                  .all())
    totals_by_day = {d: float(t) for d, t in daily_rows}
    daily = [(first_day + timedelta(days=i), totals_by_day.get(first_day + timedelta(days=i), 0.0))
             for i in range(today.day)]
    max_daily = max((t for _, t in daily), default=0)

    # --- "Recent transactions" table ---
    recent = (Expense.query.filter_by(user_id=current_user.id)
              .order_by(Expense.date.desc(), Expense.id.desc())
              .limit(6).all())

    return render_template(
        "main/dashboard.html",
        spent=spent, budget=budget, left=left, percent=percent,
        days_passed=days_passed, days_left=days_left,
        daily_avg=daily_avg, per_day_left=per_day_left,
        by_category=by_category, donut_gradient=donut_gradient,
        daily=daily, max_daily=max_daily, first_day=first_day,
        recent=recent,
    )