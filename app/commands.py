import click

from .extensions import db
from .models import User, Category

DEFAULT_CATEGORIES = [
    ("Food", "#f59f00", "🍔"),
    ("Transport", "#206bc4", "🚗"),
    ("Housing", "#ae3ec9", "🏠"),
    ("Bills", "#d63939", "💡"),
    ("Health", "#2fb344", "💊"),
    ("Entertainment", "#f76707", "🎬"),
    ("Shopping", "#d6336c", "🛍️"),
    ("Other", "#667382", "🏷️"),
]


def register_commands(app):

    @app.cli.command("seed")
    def seed():
        """Create the default categories."""
        created = 0
        for name, color, icon in DEFAULT_CATEGORIES:
            if not Category.query.filter_by(name=name).first():
                db.session.add(Category(name=name, color=color, icon=icon))
                created += 1
        db.session.commit()
        click.echo(f"Created {created} categories.")

    @app.cli.command("create-admin")
    @click.argument("username")
    @click.argument("email")
    @click.password_option()
    def create_admin(username, email, password):
        """Create an admin user: flask create-admin USERNAME EMAIL"""
        if User.query.filter((User.username == username) | (User.email == email)).first():
            click.echo("A user with that username or email already exists.")
            return
        admin = User(username=username, email=email, role="admin")
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Admin '{username}' created.")