from flask_wtf import FlaskForm
from sqlalchemy import func
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp, ValidationError

from ..models import Category


class CategoryForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=50)])
    color = StringField("Color", default="#2f8fe0", validators=[
        DataRequired(),
        Regexp(r"^#[0-9a-fA-F]{6}$", message="Use a hex color like #2f8fe0."),
    ])
    icon = StringField("Icon (emoji)", default="🏷️", validators=[DataRequired(), Length(max=10)])
    submit = SubmitField("Save category")

    def __init__(self, *args, category_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.category_id = category_id      # the category being edited (None when adding)

    def validate_name(self, field):
        existing = Category.query.filter(func.lower(Category.name) == field.data.strip().lower()).first()
        if existing and existing.id != self.category_id:
            raise ValidationError("A category with this name already exists.")