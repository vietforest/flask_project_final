"""
JSON REST API.  All URLs start with /api  (see app/__init__.py)

  GET     /api/categories
  GET     /api/expenses            ?q= &category= &month=YYYY-MM &page= &per_page=
  POST    /api/expenses            {"amount", "description", "date", "category_id"}
  GET     /api/expenses/<id>
  PUT     /api/expenses/<id>       all fields
  PATCH   /api/expenses/<id>       only the fields you want to change
  DELETE  /api/expenses/<id>
  GET     /api/summary             ?month=YYYY-MM

Every endpoint needs a logged-in user and only works with THAT user's expenses.
"""
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import jsonify, request, url_for
from flask_login import login_required, current_user

from . import api_bp
from ..extensions import db
from ..models import Expense, Category
from ..services import expense_query, month_range, month_summary


# ---------------------------------------------------------------- helpers

def error(message, status, details=None):
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def get_own_expense(expense_id):
    """The expense if it belongs to the current user, otherwise None.
    The API answers 404 in both cases, so nobody can find out which ids exist."""
    expense = db.session.get(Expense, expense_id)
    if expense is None or expense.user_id != current_user.id:
        return None
    return expense


def validate_expense(data, partial=False):
    """Check the JSON sent by the client.
    Returns (clean_values, errors). With partial=True missing fields are allowed (PATCH)."""
    values, errors = {}, {}

    if "amount" in data:
        try:
            amount = Decimal(str(data["amount"]))
            if not (Decimal("0.01") <= amount <= Decimal("1000000")):
                raise ValueError
            values["amount"] = amount.quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError, TypeError):
            errors["amount"] = "Must be a number between 0.01 and 1000000."
    elif not partial:
        errors["amount"] = "Required."

    if "description" in data:
        description = str(data["description"] or "").strip()
        if not description or len(description) > 200:
            errors["description"] = "Required, max 200 characters."
        else:
            values["description"] = description
    elif not partial:
        errors["description"] = "Required."

    if "date" in data:
        try:
            day = date.fromisoformat(str(data["date"]))
            if day > date.today():
                errors["date"] = "Can't be in the future."
            else:
                values["date"] = day
        except ValueError:
            errors["date"] = "Use the format YYYY-MM-DD."
    elif not partial:
        values["date"] = date.today()          # default: today

    if "category_id" in data:
        category = None
        if isinstance(data["category_id"], int) and not isinstance(data["category_id"], bool):
            category = db.session.get(Category, data["category_id"])
        if category is None:
            errors["category_id"] = "Unknown category."
        else:
            values["category_id"] = category.id
    elif not partial:
        errors["category_id"] = "Required."

    return values, errors


# ---------------------------------------------------------------- categories

@api_bp.route("/categories", methods=["GET"])
@login_required
def list_categories():
    categories = Category.query.order_by(Category.name).all()
    return jsonify([c.to_dict() for c in categories])


# ---------------------------------------------------------------- expenses

@api_bp.route("/expenses", methods=["GET"])
@login_required
def list_expenses():
    if request.args.get("month") and month_range(request.args["month"])[0] is None:
        return error("Invalid month, use YYYY-MM.", 400)

    query = expense_query(
        current_user.id,
        q=request.args.get("q", "").strip(),
        category_id=request.args.get("category", type=int),
        month=request.args.get("month", ""),
    )
    per_page = min(request.args.get("per_page", 20, type=int), 100)   # max 100 per page
    page = (query.order_by(Expense.date.desc(), Expense.id.desc())
            .paginate(page=request.args.get("page", 1, type=int), per_page=per_page, error_out=False))

    return jsonify({
        "items": [e.to_dict() for e in page.items],
        "page": page.page,
        "pages": page.pages,
        "per_page": per_page,
        "total": page.total,
    })


@api_bp.route("/expenses", methods=["POST"])
@login_required
def create_expense():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error("Send a JSON object.", 400)

    values, errors = validate_expense(data)
    if errors:
        return error("Invalid data.", 400, errors)

    expense = Expense(user_id=current_user.id, **values)
    db.session.add(expense)
    db.session.commit()

    response = jsonify(expense.to_dict())
    response.status_code = 201                                    # 201 Created
    response.headers["Location"] = url_for("api.get_expense", expense_id=expense.id)
    return response


@api_bp.route("/expenses/<int:expense_id>", methods=["GET"])
@login_required
def get_expense(expense_id):
    expense = get_own_expense(expense_id)
    if expense is None:
        return error("Expense not found.", 404)
    return jsonify(expense.to_dict())


@api_bp.route("/expenses/<int:expense_id>", methods=["PUT", "PATCH"])
@login_required
def update_expense(expense_id):
    expense = get_own_expense(expense_id)
    if expense is None:
        return error("Expense not found.", 404)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error("Send a JSON object.", 400)

    values, errors = validate_expense(data, partial=(request.method == "PATCH"))
    if errors:
        return error("Invalid data.", 400, errors)

    for field, value in values.items():
        setattr(expense, field, value)
    db.session.commit()
    return jsonify(expense.to_dict())


@api_bp.route("/expenses/<int:expense_id>", methods=["DELETE"])
@login_required
def delete_expense(expense_id):
    expense = get_own_expense(expense_id)
    if expense is None:
        return error("Expense not found.", 404)
    db.session.delete(expense)
    db.session.commit()
    return "", 204                                                # 204 No Content


# ---------------------------------------------------------------- summary

@api_bp.route("/summary", methods=["GET"])
@login_required
def summary():
    month = request.args.get("month", "")
    first_day = None
    if month:
        first_day, _ = month_range(month)
        if first_day is None:
            return error("Invalid month, use YYYY-MM.", 400)

    s = month_summary(current_user, first_day)
    return jsonify({
        "month": s["first_day"].strftime("%Y-%m"),
        "spent": round(s["spent"], 2),
        "budget": s["budget"],
        "left": round(s["left"], 2),
        "percent": s["percent"],
        "count": s["count"],
        "daily_average": round(s["daily_avg"], 2),
        "by_category": [
            {**cat.to_dict(), "total": round(total, 2)} for cat, total in s["by_category"]
        ],
        "daily": [{"date": d.isoformat(), "total": round(t, 2)} for d, t in s["daily"]],
    })