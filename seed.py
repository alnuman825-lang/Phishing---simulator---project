"""
Seed the database with phishing training scenarios.

Idempotent: running this multiple times will NOT create duplicate
scenarios — it matches on `title` and only inserts scenarios that
aren't already present, and updates existing ones so edits to
app/seed_data.py are picked up on re-run.

Usage:
    python seed.py
"""

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import db
from app.models.scenario import Scenario
from app.seed_data import SCENARIOS


def seed():
    app = create_app()
    with app.app_context():
        created, updated = 0, 0

        for data in SCENARIOS:
            existing = Scenario.query.filter_by(title=data["title"]).first()
            if existing:
                for key, value in data.items():
                    setattr(existing, key, value)
                updated += 1
            else:
                db.session.add(Scenario(**data))
                created += 1

        db.session.commit()
        total = Scenario.query.count()
        print(f"Seed complete: {created} created, {updated} updated, {total} total scenarios in database.")


if __name__ == "__main__":
    seed()
