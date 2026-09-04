# database/

This folder is a placeholder for database-related assets that aren't
Python models (e.g. raw SQL seed scripts, ER diagrams).

Flask-Migrate will generate its own `migrations/` folder at the
project root the first time you run `flask db init` — see the main
README for the exact commands. That generated folder is intentionally
separate from this one so migration history isn't mixed with
hand-written SQL/docs.
