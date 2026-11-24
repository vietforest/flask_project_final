from flask import render_template, redirect, url_for, flash
from flask_login import current_user
from sqlalchemy import func

from . import admin_bp
from .forms import CategoryForm
from ..decorators import admin_required
from ..extensions import db
from ..models import User, Category, Expense


# ---------------------------------------------------------------- users

@admin_bp.route("/users")
@admin_required
def users():
    # each user + how many expenses they have, in ONE query
    rows = (db.session.query(User, func.count(Expense.id))
            .outerjoin(Expense, Expense.user_id == User.id)
            .group_by(User.id)
            .order_by(User.username)
            .all())
    return render_template("admin/users.html", rows=rows)


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
@admin_required
def toggle_role(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("You can't change your own role.", "warning")
    else:
        user.role = "user" if user.is_admin else "admin"
        db.session.commit()
        flash(f"{user.username} is now {user.role}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("You can't delete your own account here.", "warning")
    else:
        db.session.delete(user)          # their expenses are deleted too (cascade in models.py)
        db.session.commit()
        flash(f"User {user.username} deleted.", "info")
    return redirect(url_for("admin.users"))


# ---------------------------------------------------------------- categories

@admin_bp.route("/categories", methods=["GET", "POST"])
@admin_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        db.session.add(Category(name=form.name.data.strip(),
                                color=form.color.data.lower(),
                                icon=form.icon.data.strip()))
        db.session.commit()
        flash("Category added.", "success")
        return redirect(url_for("admin.categories"))

    rows = (db.session.query(Category, func.count(Expense.id))
            .outerjoin(Expense, Expense.category_id == Category.id)
            .group_by(Category.id)
            .order_by(Category.name)
            .all())
    return render_template("admin/categories.html", rows=rows, form=form)


@admin_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_category(category_id):
    category = db.get_or_404(Category, category_id)
    form = CategoryForm(obj=category, category_id=category.id)
    if form.validate_on_submit():
        category.name = form.name.data.strip()
        category.color = form.color.data.lower()
        category.icon = form.icon.data.strip()
        db.session.commit()
        flash("Category updated.", "success")
        return redirect(url_for("admin.categories"))
    return render_template("admin/category_form.html", form=form, category=category)


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@admin_required
def delete_category(category_id):
    category = db.get_or_404(Category, category_id)
    used = Expense.query.filter_by(category_id=category.id).count()
    if used:
        flash(f"Can't delete {category.name}: {used} expenses use it.", "danger")
    else:
        db.session.delete(category)
        db.session.commit()
        flash(f"Category {category.name} deleted.", "info")
    return redirect(url_for("admin.categories"))