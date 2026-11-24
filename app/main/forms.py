from datetime import date

from flask_wtf import FlaskForm
from wtforms import DecimalField, StringField, DateField, SelectField, SubmitField, PasswordField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, ValidationError, EqualTo


class ExpenseForm(FlaskForm):
    amount = DecimalField("Amount", places=2, validators=[
        InputRequired(message="Enter an amount."),   # InputRequired: 0 is a value, not "empty"
        NumberRange(min=0.01, max=1_000_000, message="Amount must be between 0.01 and 1,000,000."),
    ])
    description = StringField("Description", validators=[DataRequired(), Length(max=200)])
    date = DateField("Date", default=date.today, validators=[DataRequired()])
    # the choices (list of categories) are filled in by the route
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Save expense")

    def validate_date(self, field):
        if field.data and field.data > date.today():
            raise ValidationError("The date can't be in the future.")

class BudgetForm(FlaskForm):
    monthly_budget = DecimalField("Monthly budget", places=2, validators=[
        InputRequired(message="Enter a budget."),
        NumberRange(min=1, max=1_000_000, message="Budget must be between 1 and 1,000,000."),
    ])
    submit_budget = SubmitField("Save budget")


class PasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=8)])
    confirm = PasswordField("Repeat new password", validators=[
        DataRequired(), EqualTo("new_password", message="Passwords must match."),
    ])
    submit_password = SubmitField("Change password")        