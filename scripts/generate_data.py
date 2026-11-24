"""
Generate synthetic (fake but realistic) transactions for the Expense Tracker.

Creates a CSV with 12 months of expenses:
  - fixed monthly costs (rent, internet, phone, streaming)
  - bills that change with the season (electricity, gas)
  - everyday spending (groceries, coffee, transport, eating out...)
  - more shopping in November/December

Usage (from the project root, with the venv active):
    python scripts/generate_data.py
    python scripts/generate_data.py --months 12 --seed 42 --output data/transactions.csv

Then load it into the database for a user:
    flask import-csv data/transactions.csv --user demo
"""
import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

# Category names must match the categories in the database (flask seed)
CATEGORIES = ["Food", "Transport", "Housing", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def month_starts(months):
    """First day of each of the last `months` months, oldest first (current month included)."""
    first = date.today().replace(day=1)
    result = []
    for _ in range(months):
        result.append(first)
        first = (first - timedelta(days=1)).replace(day=1)
    return list(reversed(result))


def add(rows, day, description, category, amount):
    """Add one transaction (only if the day is not in the future)."""
    if day <= date.today():
        rows.append({
            "date": day,
            "description": description,
            "category": category,
            "amount": round(amount, 2),
        })


def generate(months, fake):
    rows = []

    for start in month_starts(months):
        next_month = (start + timedelta(days=32)).replace(day=1)
        winter = start.month in (11, 12, 1, 2)

        # ---- fixed monthly costs ----
        add(rows, start, "Monthly rent", "Housing", 450.00)
        add(rows, start + timedelta(days=4), "Internet - FiberNet", "Bills", 27.90)
        add(rows, start + timedelta(days=9), "Phone plan", "Bills", 9.99)
        add(rows, start + timedelta(days=14), "Netflix subscription", "Entertainment", 13.99)
        add(rows, start + timedelta(days=2), "Gym membership", "Health", 35.00)

        # ---- seasonal bills ----
        electricity = random.uniform(70, 110) if winter else random.uniform(40, 65)
        add(rows, start + timedelta(days=19), "Electricity bill", "Bills", electricity)
        if winter:
            add(rows, start + timedelta(days=21), "Gas heating bill", "Bills", random.uniform(60, 120))

        # ---- day by day ----
        day = start
        while day < next_month:
            weekend = day.weekday() >= 5

            # groceries about twice a week
            if day.weekday() in (1, 5) or random.random() < 0.08:
                add(rows, day, f"Groceries - {fake.last_name()} Market", "Food", random.uniform(18, 75))

            # coffee on most weekdays
            if not weekend and random.random() < 0.55:
                add(rows, day, "Coffee & croissant", "Food", random.uniform(1.8, 4.5))

            # eating out, mostly at weekends
            if random.random() < (0.45 if weekend else 0.12):
                place = random.choice(["Pizzeria", "Trattoria", "Sushi bar", "Burger place", "Kebab"])
                add(rows, day, f"{place} {fake.last_name()}", "Food", random.uniform(9, 38))

            # transport: commute on weekdays, sometimes fuel or taxi
            if not weekend and random.random() < 0.7:
                add(rows, day, "Bus / metro ticket", "Transport", 2.20)
            if random.random() < 0.06:
                add(rows, day, "Fuel", "Transport", random.uniform(35, 65))
            if random.random() < 0.03:
                add(rows, day, "Taxi ride", "Transport", random.uniform(10, 28))

            # entertainment at weekends
            if weekend and random.random() < 0.3:
                what = random.choice(["Cinema tickets", "Concert", "Bowling", "Museum", "Video game"])
                add(rows, day, what, "Entertainment", random.uniform(8, 45))

            # shopping: more in November and December (Black Friday, Christmas)
            shop_chance = 0.12 if start.month in (11, 12) else 0.04
            if random.random() < shop_chance:
                item = random.choice(["Clothes", "Shoes", "Headphones", "Gift", "Books", "Phone case"])
                add(rows, day, f"{item} - {fake.last_name()} Store", "Shopping", random.uniform(12, 120))

            # health: pharmacy now and then
            if random.random() < 0.04:
                add(rows, day, "Pharmacy", "Health", random.uniform(5, 30))

            # other
            if random.random() < 0.03:
                what = random.choice(["Haircut", "Stationery", "Donation", "Dry cleaning"])
                add(rows, day, what, "Other", random.uniform(5, 30))

            day += timedelta(days=1)

    return rows


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic expense transactions as CSV.")
    parser.add_argument("--months", type=int, default=12, help="how many months back (default: 12)")
    parser.add_argument("--seed", type=int, default=None, help="random seed, same seed = same data")
    parser.add_argument("--output", default="data/transactions.csv", help="CSV file to write")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        Faker.seed(args.seed)
    fake = Faker("it_IT")  # Italian names for shops and restaurants

    # ---- pandas: build, sort and save the table ----
    df = pd.DataFrame(generate(args.months, fake))
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False, date_format="%Y-%m-%d", float_format="%.2f")

    # ---- pandas: print a short summary ----
    print(f"Saved {len(df)} transactions to {output}\n")

    per_month = df.groupby(df["date"].dt.to_period("M"))["amount"].sum().round(2)
    print("Total per month:")
    print(per_month.to_string(), "\n")

    per_category = df.groupby("category")["amount"].agg(["count", "sum"]).round(2)
    print("Per category:")
    print(per_category.sort_values("sum", ascending=False).to_string())


if __name__ == "__main__":
    main()