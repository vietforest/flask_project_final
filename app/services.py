"""
Shared logic used by both the web pages (main blueprint) and the API.
Keeping it here means the dashboard and /api/summary always give the same numbers.
"""
from datetime import date, datetime, timedelta

from sqlalchemy import func

from .extensions import db
from .models import Expense, Category


def month_range(value):
    """'2026-11' -> (date(2026, 11, 1), date(2026, 12, 1)). Invalid or empty -> (None, None)."""
    try:
        start = datetime.strptime(value, "%Y-%m").date()
    except (TypeError, ValueError):
        return None, None
    return start, (start + timedelta(days=32)).replace(day=1)


def expense_query(user_id, q="", category_id=None, month=""):
    """Expenses of ONE user, with optional filters. Returns a query (not yet executed)."""
    query = Expense.query.filter_by(user_id=user_id)
    if q:
        query = query.filter(Expense.description.ilike(f"%{q}%"))
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    start, end = month_range(month)
    if start:
        query = query.filter(Expense.date >= start, Expense.date < end)
    return query


def month_summary(user, first_day=None):
    """All the numbers of the dashboard for one user and one month (default: this month)."""
    today = date.today()
    first_day = first_day or today.replace(day=1)
    next_month = (first_day + timedelta(days=32)).replace(day=1)
    days_in_month = (next_month - first_day).days

    # for a past month every day counts; for the current month only up to today
    is_current = first_day <= today < next_month
    days_passed = today.day if is_current else days_in_month
    days_left = days_in_month - today.day if is_current else 0

    this_month = (
        Expense.user_id == user.id,
        Expense.date >= first_day,
        Expense.date < next_month,
    )

    spent = float(db.session.query(func.coalesce(func.sum(Expense.amount), 0))
                  .filter(*this_month).scalar())
    count = db.session.query(func.count(Expense.id)).filter(*this_month).scalar()
    budget = float(user.monthly_budget)
    left = budget - spent

    rows = (db.session.query(Category, func.sum(Expense.amount))
            .join(Expense, Expense.category_id == Category.id)
            .filter(*this_month)
            .group_by(Category.id)
            .order_by(func.sum(Expense.amount).desc())
            .all())
    by_category = [(cat, float(total)) for cat, total in rows]

    daily_rows = (db.session.query(Expense.date, func.sum(Expense.amount))
                  .filter(*this_month)
                  .group_by(Expense.date)
                  .all())
    totals_by_day = {d: float(t) for d, t in daily_rows}
    daily = [(first_day + timedelta(days=i), totals_by_day.get(first_day + timedelta(days=i), 0.0))
             for i in range(days_passed)]

    return {
        "first_day": first_day,
        "spent": spent,
        "count": count,
        "budget": budget,
        "left": left,
        "percent": min(round(spent / budget * 100), 100) if budget else 0,
        "days_passed": days_passed,
        "days_left": days_left,
        "daily_avg": spent / days_passed if days_passed else 0,
        "per_day_left": (left / days_left) if days_left > 0 and left > 0 else 0,
        "by_category": by_category,
        "daily": daily,
        "max_daily": max((t for _, t in daily), default=0),
    }