import csv
import io
from datetime import date

from flask import (render_template, redirect, url_for, flash, request,
                   abort, current_app, Response)
from flask_login import login_required, current_user
from sqlalchemy import func

from . import main_bp
from ..extensions import db
from ..models import Expense, Category
from ..services import expense_query, month_summary
from .forms import ExpenseForm, BudgetForm, PasswordForm

@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("main/index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    stats = month_summary(current_user)          # all the numbers (see app/services.py)

    # build a CSS conic-gradient like "#f59f00 0% 32%, #206bc4 32% 50%, ..."
    stops, start = [], 0.0
    for cat, total in stats["by_category"]:
        end = start + (total / stats["spent"] * 100 if stats["spent"] else 0)
        stops.append(f"{cat.color} {start:.2f}% {end:.2f}%")
        start = end
    donut_gradient = f"conic-gradient({', '.join(stops)})" if stops else "none"

    recent = (Expense.query.filter_by(user_id=current_user.id)
              .order_by(Expense.date.desc(), Expense.id.desc())
              .limit(6).all())

    return render_template("main/dashboard.html", **stats,
                           donut_gradient=donut_gradient, recent=recent)

# =====================================================================
#  STEP 5: Expenses CRUD
# =====================================================================



def category_choices():
    return [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]


def get_own_expense_or_403(expense_id):
    """Load an expense; 404 if it doesn't exist, 403 if it belongs to someone else."""
    expense = db.get_or_404(Expense, expense_id)
    if expense.user_id != current_user.id:
        abort(403)
    return expense


def filtered_expenses():
    """Expenses of the current user, filtered by the ?q= &category= &month= in the URL."""
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)
    month = request.args.get("month", "")

    query = expense_query(current_user.id, q=q, category_id=category_id, month=month)

    # only keep the filters that are actually used (for links and the form)
    filters = {k: v for k, v in {"q": q, "category": category_id, "month": month}.items() if v}
    return query, filters

@main_bp.route("/expenses")
@login_required
def expenses():
    query, filters = filtered_expenses()

    total = float(query.with_entities(func.coalesce(func.sum(Expense.amount), 0)).scalar())
    pagination = (query.order_by(Expense.date.desc(), Expense.id.desc())
                  .paginate(page=request.args.get("page", 1, type=int),
                            per_page=current_app.config["ITEMS_PER_PAGE"],
                            error_out=False))

    return render_template("main/expenses.html",
                           pagination=pagination, total=total, filters=filters,
                           categories=Category.query.order_by(Category.name).all())


@main_bp.route("/expenses/new", methods=["GET", "POST"])
@login_required
def expense_new():
    form = ExpenseForm()
    form.category_id.choices = category_choices()

    if form.validate_on_submit():
        expense = Expense(
            user_id=current_user.id,          # always the logged-in user
            amount=form.amount.data,
            description=form.description.data.strip(),
            date=form.date.data,
            category_id=form.category_id.data,
        )
        db.session.add(expense)
        db.session.commit()
        flash("Expense added.", "success")
        return redirect(url_for("main.expenses"))

    return render_template("main/expense_form.html", form=form, title="Add expense")


@main_bp.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def expense_edit(expense_id):
    expense = get_own_expense_or_403(expense_id)
    form = ExpenseForm(obj=expense)           # fill the form with the current values
    form.category_id.choices = category_choices()

    if form.validate_on_submit():
        expense.amount = form.amount.data
        expense.description = form.description.data.strip()
        expense.date = form.date.data
        expense.category_id = form.category_id.data
        db.session.commit()
        flash("Expense updated.", "success")
        return redirect(url_for("main.expenses"))

    return render_template("main/expense_form.html", form=form, title="Edit expense", expense=expense)


@main_bp.route("/expenses/<int:expense_id>/delete", methods=["POST"])
@login_required
def expense_delete(expense_id):
    expense = get_own_expense_or_403(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted.", "info")
    return redirect(url_for("main.expenses"))


@main_bp.route("/expenses/export.csv")
@login_required
def expenses_export():
    """Download the (filtered) expenses as CSV - same format as scripts/generate_data.py."""
    query, _ = filtered_expenses()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "description", "category", "amount"])
    for e in query.order_by(Expense.date):
        writer.writerow([e.date.isoformat(), e.description, e.category.name, f"{e.amount:.2f}"])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=expenses_{date.today()}.csv"},
    )

# =====================================================================
#  STEP 7: Settings (every user)
# =====================================================================

def render_settings(budget_form=None, password_form=None):
    # formdata=None: a form that was NOT submitted must not read the other form's data
    return render_template(
        "main/settings.html",
        budget_form=budget_form or BudgetForm(formdata=None, monthly_budget=current_user.monthly_budget),
        password_form=password_form or PasswordForm(formdata=None),
    )


@main_bp.route("/settings")
@login_required
def settings():
    return render_settings()


@main_bp.route("/settings/budget", methods=["POST"])
@login_required
def settings_budget():
    form = BudgetForm()
    if form.validate_on_submit():
        current_user.monthly_budget = form.monthly_budget.data
        db.session.commit()
        flash("Monthly budget saved.", "success")
        return redirect(url_for("main.settings"))
    return render_settings(budget_form=form)


@main_bp.route("/settings/password", methods=["POST"])
@login_required
def settings_password():
    form = PasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            form.current_password.errors.append("Wrong password.")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Password changed.", "success")
            return redirect(url_for("main.settings"))
    return render_settings(password_form=form)