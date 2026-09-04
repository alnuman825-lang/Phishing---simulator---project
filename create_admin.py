"""
Create or promote an admin account.

Interactive by design — the password is entered via a hidden prompt
(getpass) and never appears in shell history, a script argument, or
this file. This keeps admin creation consistent with the "no
hard-coded credentials" security requirement.

Usage:
    python create_admin.py
"""

import sys
from getpass import getpass

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import db
from app.models.user import User


def create_admin():
    app = create_app()
    with app.app_context():
        email = input("Admin email: ").strip().lower()
        existing = User.query.filter_by(email=email).first()

        if existing:
            if existing.is_admin:
                print(f"{email} is already an admin. Nothing to do.")
                return
            confirm = input(f"{email} already exists as a regular user. Promote to admin? [y/N]: ")
            if confirm.lower() != "y":
                print("Cancelled.")
                return
            existing.role = "admin"
            db.session.commit()
            print(f"{email} promoted to admin.")
            return

        name = input("Admin name: ").strip()
        password = getpass("Admin password (min 8 chars): ")
        confirm_password = getpass("Confirm password: ")

        if password != confirm_password:
            print("Passwords do not match. Aborting.", file=sys.stderr)
            sys.exit(1)
        if len(password) < 8:
            print("Password must be at least 8 characters. Aborting.", file=sys.stderr)
            sys.exit(1)

        admin = User(name=name, email=email, role="admin")
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin account created for {email}.")


if __name__ == "__main__":
    create_admin()
