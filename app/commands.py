import random
from datetime import date, timedelta
from decimal import Decimal

import click

from .extensions import db
from .models import User, Category, Expense


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

    @app.cli.command("seed-demo")
    @click.option("--expenses", default=60, help="How many fake expenses to create.")
    def seed_demo(expenses):
        """Create demo users with random expenses (for testing / presentation)."""
        categories = Category.query.all()
        if not categories:
            click.echo("No categories found. Run `flask seed` first.")
            return

        demo_users = [
            ("demo", "demo@example.com", "demo1234", "user"),
            ("mario", "mario@example.com", "mario1234", "user"),
            ("admin_demo", "admin_demo@example.com", "admin1234", "admin"),
        ]

        # fake descriptions for each category
        samples = {
            "Food": ["Supermarket", "Pizza", "Coffee", "Lunch at school", "Sushi"],
            "Transport": ["Train ticket", "Bus pass", "Fuel", "Taxi", "Parking"],
            "Housing": ["Rent", "Furniture", "Cleaning products"],
            "Bills": ["Electricity", "Internet", "Phone", "Water", "Gas"],
            "Health": ["Pharmacy", "Doctor visit", "Gym"],
            "Entertainment": ["Cinema", "Concert", "Netflix", "Video game", "Books"],
            "Shopping": ["Clothes", "Shoes", "Headphones", "Gift"],
            "Other": ["Haircut", "Donation", "Stationery"],
        }

        today = date.today()
        for username, email, password, role in demo_users:
            user = User.query.filter_by(username=username).first()
            if user:
                click.echo(f"User '{username}' already exists, skipped.")
                continue

            user = User(username=username, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()  # gives user.id before commit

            # admins don't need expenses
            if role == "admin":
                continue

            for _ in range(expenses):
                category = random.choice(categories)
                description = random.choice(samples.get(category.name, ["Expense"]))
                amount = Decimal(str(round(random.uniform(2, 120), 2)))
                if category.name == "Housing" and description == "Rent":
                    amount = Decimal("450.00")
                db.session.add(Expense(
                    user_id=user.id,
                    category_id=category.id,
                    description=description,
                    amount=amount,
                    date=today - timedelta(days=random.randint(0, 180)),  # last 6 months
                ))

        db.session.commit()
        click.echo("Demo data created. Logins:")
        for username, _, password, role in demo_users:
            click.echo(f"  {username} / {password}  ({role})")    