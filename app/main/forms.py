from datetime import date

from flask_wtf import FlaskForm
from wtforms import DecimalField, StringField, DateField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError


class ExpenseForm(FlaskForm):
    amount = DecimalField("Amount", places=2, validators=[
        DataRequired(message="Enter an amount."),
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