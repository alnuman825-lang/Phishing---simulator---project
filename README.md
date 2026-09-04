# CyberShield — AI-Powered Phishing Simulator and Training Portal

## Purpose

CyberShield is a controlled cybersecurity awareness training web
application built for a CSU university software development project.
It presents users with **simulated** phishing scenarios, records how
they respond, and gives immediate educational feedback.

**This system does not send real phishing emails and does not collect
real credentials.** All scenario content is fictional training
material, clearly labelled as simulated.

## Technology stack

- Python 3 / Flask (application factory pattern, Blueprints)
- Flask-SQLAlchemy (ORM) + Flask-Migrate (schema migrations)
- Flask-Login (session-based auth)
- Flask-WTF / WTForms (forms, validation, CSRF protection)
- PostgreSQL (production/dev database)
- HTML / CSS / vanilla JS (server-rendered templates, minimal JS)
- pytest (automated tests)

## Project structure

```
CyberShield/
  app/
    __init__.py        # application factory
    config.py           # env-driven configuration
    extensions.py        # db, migrate, login_manager, csrf instances
    forms.py             # WTForms (registration, login)
    models/
      user.py
      scenario.py
      response.py
    routes/
      auth.py            # register / login / logout
      dashboard.py        # dashboard + root redirect
    templates/
      base.html, register.html, login.html, dashboard.html
    static/
      css/style.css
      js/main.js
  tests/
    conftest.py
    test_auth.py
  database/               # non-Python DB assets / notes
  .env.example
  .gitignore
  requirements.txt
  run.py
```

## Current implemented functionality

### Stage 1 — authentication & dashboard shell
- User registration with server-side validation, duplicate-email
  prevention, and PBKDF2 password hashing (`werkzeug.security`) —
  no plaintext passwords are ever stored.
- User login with hashed password verification and secure, HttpOnly
  session cookies (via Flask-Login).
- Protected dashboard route (`/dashboard`) that redirects
  unauthenticated users to `/login`.
- CSRF protection on all forms (Flask-WTF).
- Database schema for `users`, `scenarios`, and `responses`.

### Stage 2 — phishing simulation & training workflow
- **6 simulated phishing scenarios** (more than the required 5),
  covering: fake university account suspension, suspicious password
  reset, fake parcel delivery, fake invoice/payment, a typosquatted
  Microsoft-style alert, and one legitimate-looking internal survey
  (included so users learn not to reflexively report everything).
  All content is fictional; see `app/seed_data.py`.
- `GET /training` — lists active scenarios for the logged-in user,
  showing which are already completed.
- `GET/POST /training/<id>` — displays the simulated email and a
  3-option response form (Click/Open, Report, Ignore/Delete). The
  correct answer is never rendered on this page. A user who has
  already attempted a scenario is redirected straight to their
  feedback instead of being able to re-attempt it.
- **Scoring** is simple and transparent, computed entirely
  server-side: correct response = 100 points, incorrect = 0. The
  client only ever sends which option was clicked — never a score or
  correctness value — and the server looks up `Scenario.correct_response`
  itself to grade it. Duplicate submissions are blocked both at the
  application level and by a `UNIQUE(user_id, scenario_id)` database
  constraint.
- `GET /training/<id>/feedback` — shows the user's own stored
  response, whether it was correct, the score earned, and the
  scenario's educational explanation.
- `GET /results` — the logged-in user's full history (scenario,
  response, correct/incorrect, score, timestamp). This route is
  scoped to `current_user.id` with no response/user ID in the URL at
  all, so there's nothing for another user to tamper with to view
  someone else's results.
- Dashboard now shows real, DB-computed stats: scenarios completed /
  total available, correct, incorrect, accuracy %, and total score /
  max possible score.
- `seed.py` — idempotent seed script for the 6 scenarios (see below).
- 10 new automated tests covering training access control, scenario
  display (answer not leaked), valid/invalid submission, correct and
  incorrect scoring, DB persistence, results isolation between users,
  and dashboard stat updates.

### Stage 3 — admin functionality
- `User.role` (already in the Stage 1 schema — no migration needed)
  now gates access via `app/authz.py`'s `@admin_required` decorator,
  stacked with `@login_required` so anonymous visitors are redirected
  to `/login` and authenticated non-admins get a `403 Forbidden`.
- `GET /admin/` — platform-wide overview: registered users, active
  scenarios, total attempts, overall accuracy.
- `GET /admin/users` — every registered user's name, email, role,
  and registration date. **Password hashes are never included in the
  route's template context**, so there's nothing to leak regardless
  of the template.
- `GET /admin/results` — every user's every attempt (user, scenario,
  response, correct/incorrect, score, timestamp) — read-only, for
  reviewing overall training outcomes.
- `GET /admin/scenarios` — per-scenario attempt count, correct count,
  and accuracy %, to spot which phishing indicators students
  struggle with.
- `create_admin.py` — interactive script to create a new admin
  account or promote an existing user. The password is entered via a
  hidden `getpass` prompt — it's never a command-line argument, never
  hard-coded, and never written to shell history.
- 7 new tests covering: anonymous → redirected to login, regular
  user → 403 on `/admin/` and all three sub-pages, admin → 200 on all
  pages, users page never renders a password hash, results page
  shows all users' attempts, scenario page computes accuracy correctly.

**Not yet implemented:** editing/deleting users or scenarios from the
admin UI (Stage 3 is intentionally read-only), pagination on the
results/users tables (fine at prototype scale, would need it for a
large class). Each scenario can only be attempted once per user
(by design); scoring is binary (100/0), no partial credit.

## Creating an admin account

```bash
python create_admin.py
```

You'll be prompted for an email, name, and password (hidden input,
via `getpass` — never a CLI argument, never hard-coded). If the email
already belongs to an existing regular user, the script offers to
promote that account to admin instead of creating a duplicate.

## Prerequisites

- Python 3.10+
- PostgreSQL 14+ installed and running locally
- `pip`

## Installation

```bash
# 1. Clone your repo and enter it
cd CyberShield

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the environment template and fill in real local values
cp .env.example .env
```

Edit `.env` and set at least:

```
SECRET_KEY=<generate a long random string>
DATABASE_URL=postgresql://cybershield_user:changeme@localhost:5432/cybershield
```

Generate a secret key quickly with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Database setup (PostgreSQL)

```bash
# Create the database and a dedicated user (run inside psql or via createdb/createuser)
createuser cybershield_user --pwprompt
createdb cybershield --owner=cybershield_user
```

Then initialise and apply migrations:

```bash
flask --app run.py db init        # first time only, creates migrations/
flask --app run.py db migrate -m "Initial users/scenarios/responses tables"
flask --app run.py db upgrade
```

## Seeding the phishing scenarios

After running migrations (so the `scenarios` table exists), populate
it with the training content:

```bash
python seed.py
```

This is safe to re-run at any time — it matches scenarios by title,
so re-running updates existing scenarios (if you edit
`app/seed_data.py`) instead of creating duplicates.

## Running the application

```bash
python run.py
```

The app runs at `http://127.0.0.1:5000`. Visit `/register` to create
an account, log in at `/login`, then go to `/training` to start a
scenario.

## Implemented routes

| Route | Method(s) | Auth required | Purpose |
|---|---|---|---|
| `/register` | GET, POST | No | Create an account |
| `/login` | GET, POST | No | Log in |
| `/logout` | GET | Yes | End session |
| `/dashboard` | GET | Yes | Progress overview |
| `/training` | GET | Yes | List scenarios + completion status |
| `/training/<id>` | GET, POST | Yes | View scenario / submit a response |
| `/training/<id>/feedback` | GET | Yes | View your own graded result for that scenario |
| `/results` | GET | Yes | Your full training history |
| `/admin/` | GET | Admin only | Platform-wide overview stats |
| `/admin/users` | GET | Admin only | List all registered users (no password hashes) |
| `/admin/results` | GET | Admin only | Every user's every training attempt |
| `/admin/scenarios` | GET | Admin only | Per-scenario attempt count / accuracy |

## Running the tests

Tests run against an in-memory SQLite database (see `TestingConfig`
in `app/config.py`), so no PostgreSQL connection is required to run
them:

```bash
pytest
# or, verbose:
pytest -v
```

All 24 tests (7 Stage 1 + 10 Stage 2 + 7 Stage 3) should pass.

## Environment variables reference

| Variable          | Purpose                                              |
|-------------------|-------------------------------------------------------|
| `FLASK_CONFIG`    | `development`, `production`, or `testing`             |
| `SECRET_KEY`      | Flask session/CSRF signing key — never commit a real one |
| `DATABASE_URL`    | PostgreSQL connection string                          |
| `TEST_DATABASE_URL` | Optional override for the test suite's DB (defaults to in-memory SQLite) |
| `PORT`            | Local port to run on (default 5000)                   |

## Development stages / commit plan

1. Initial Flask project setup *(Stage 1)*
2. Database and configuration *(Stage 1)*
3. User authentication *(Stage 1)*
4. Dashboard *(Stage 1, extended in Stage 2)*
5. Phishing scenario module *(Stage 2 — this delivery)*
6. Response and scoring *(Stage 2 — this delivery)*
7. Results/progress *(Stage 2 — this delivery)*
8. Admin functionality *(Stage 3 — this delivery)*
9. Testing (expanded) *(Stage 2 & 3 — this delivery)*
10. Documentation/UI improvements — ongoing
