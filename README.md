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
- pytest + pytest-cov (automated tests and coverage)

The phishing indicator analysis shown on the feedback and analytics
pages is **rule-based keyword matching** (`app/services/phishing_analyzer.py`).
The application does not use a machine-learning model or any external
AI service, and scenario content is fixed seed data, not generated.

## Project structure

```
(repository root)
  app/
    __init__.py            # application factory, blueprint registration, user loader
    config.py              # env-driven configuration (development / production / testing)
    extensions.py          # db, migrate, login_manager, csrf instances
    authz.py               # @admin_required decorator
    forms.py               # WTForms (registration, login)
    seed_data.py           # the six fictional training scenarios
    models/
      user.py
      scenario.py
      response.py
    routes/
      auth.py              # register / login / logout
      dashboard.py         # dashboard + root redirect
      training.py          # scenario list, attempt, feedback, own results
      admin.py             # overview, users, user detail, results, CSV, scenarios, analytics
    services/
      phishing_analyzer.py # rule-based indicator analysis
    templates/
      base.html, login.html, register.html, dashboard.html
      training_list.html, training_scenario.html, training_feedback.html, results.html
      admin/
        admin_base.html, overview.html, users.html, user_detail.html,
        results.html, scenarios.html, analytics.html
    static/
      css/style.css
      js/main.js           # placeholder; the app needs no client-side script
  migrations/              # Alembic migration history (committed)
    versions/b87a3868b698_initial_cybershield_database_schema.py
  tests/
    conftest.py              # app / client / db fixtures, plus a CSRF-enabled client
    test_auth.py             # registration, hashing, login, dashboard access
    test_training.py         # scenario display, submission, scoring, results isolation
    test_admin.py            # admin access control, analytics, user detail, CSV export
    test_phishing_analyzer.py
    test_attempt_rules.py    # one attempt per scenario, feedback access, inactive scenarios
    test_csrf.py             # CSRF protection with protection switched on
    test_seed_and_migration.py
    test_session_loading.py  # user reloaded from the session cookie on each request
  scripts/
    save_test_evidence.py  # saves raw pytest + coverage output to evidence/test-output/
  database/                # notes only (README.md)
  run.py                   # local development entry point
  seed.py                  # idempotent scenario seeding
  create_admin.py          # interactive admin creation / promotion
  requirements.txt
  .env.example             # template -- copy to .env, never commit .env
  .gitignore
  *.txt, *.docx            # earlier planning documents (ITC306 Assessment 1 and 2)
```

## Current implemented functionality

### Stage 1 — authentication & dashboard shell
- User registration with server-side validation, duplicate-email
  prevention, and salted password hashing (`werkzeug.security`, which
  uses scrypt by default in the installed Werkzeug 3.x) —
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

### Stage 4 — admin analytics, phishing analyzer integration, reporting
- **Bugfix:** `/admin/analytics` existed as a route but referenced a
  template that didn't exist (`admin/analytics.html`) and wasn't linked
  from the admin nav — visiting it threw an uncaught `TemplateNotFound`
  (500). The route is now implemented properly and linked in the nav.
- `GET /admin/analytics` — performance broken down by scenario
  **category** and **difficulty**, plus a scenario-library-wide report
  from the **PhishingAnalyzer** service (average risk score, high/
  medium/low risk scenario counts, and indicator frequency across all
  active scenarios) and a per-scenario table combining learner accuracy
  with the analyzer's risk rating for that scenario's own text — the
  first place the analyzer is used outside a single learner's feedback
  page.
- `GET /admin/users/<id>` — per-user drill-down: one user's full
  progress stats and training history, for admins reviewing a specific
  person rather than the flat all-results table. Linked from
  `/admin/users`.
- `GET /admin/results/export.csv` — downloads every recorded response
  (user, scenario, category, difficulty, response, correctness, score,
  timestamp) as CSV, for offline reporting/analysis.
- 9 new tests: analytics page loads (regression test for the fixed
  bug), category/difficulty breakdown renders, analyzer indicators
  appear on the analytics page, user-detail shows the right user's
  history, user-detail does **not** leak another user's data, CSV
  export has the right headers/content-type/rows, and the three new
  routes are added to the existing "non-admin gets 403" coverage.
- No database schema changes — analytics are computed at request time
  from the existing `users`/`scenarios`/`responses` tables plus the
  analyzer running against scenario text; no new migration needed.

### Stage 5 — QA hardening (no new features)
- Replaced the three deprecated `Query.get()` / `Query.get_or_404()`
  calls with `db.session.get()` / `db.get_or_404()`; the test suite now
  runs with no warnings.
- Pinned `SQLAlchemy==2.0.52` in `requirements.txt`. It was previously
  unpinned, and a fresh install pulled SQLAlchemy 2.1, which resolves a
  `postgresql://` URL to the `psycopg` (v3) driver. This project installs
  `psycopg2-binary`, so the app failed to start against PostgreSQL on a
  clean install.
- `migrations/env.py` now reads the engine through the non-deprecated
  Flask-SQLAlchemy attribute first.
- 32 new tests (68 in total): one attempt per scenario, duplicate
  submission prevention, feedback access with no attempt, inactive
  scenarios, CSRF protection with protection enabled, seed script
  idempotence, the committed migration (upgrade, downgrade, and the app
  running on the migrated schema), and session user loading.
- `scripts/save_test_evidence.py` saves the raw test and coverage output.

## Out of scope / not implemented

The following are **not** part of the delivered system. They are listed
so nobody assumes they exist:

- **Scenario retries (R08, MoSCoW: Could).** Each scenario can be
  attempted once per user, by design, so a learner cannot see the
  answer and then retry.
- **Progress-over-time trends (also part of R08).** The results page
  lists attempts with timestamps; there is no trend chart or comparison
  over time.
- **SMS scenarios.** All six scenarios are simulated emails.
- **AI scenario generation or any AI component.** Scenarios are fixed
  seed data and the analyzer is keyword matching.
- **Admin create / edit / delete.** Every admin page is read-only.
  Scenarios are changed by editing `app/seed_data.py` and re-running
  `seed.py`; an admin account is created with `create_admin.py`.
- **Pre/post assessment, audit logging, notifications,
  gamification/badges, pagination.**
- **Production deployment.** `run.py` starts Flask's development
  server on `127.0.0.1` only. No production web server, HTTPS setup or
  hosting configuration is included.

## Prerequisites

- Python 3.10 or newer (developed and tested on 3.13)
- PostgreSQL 14 or newer, installed and running locally
- Git

## Setup

Run every command from the repository root (the folder containing
`run.py`). Commands are given for **Windows PowerShell** and for
**macOS / Linux**; where only one block is shown it is the same on both.

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell refuses to run the activation script, allow it for the
current window only and try again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Create the PostgreSQL database and user

Open `psql` as a PostgreSQL superuser (on Windows, "SQL Shell (psql)"
from the Start menu, or `psql -U postgres`) and run:

```sql
CREATE ROLE cybershield_user LOGIN PASSWORD 'choose-a-strong-password';
CREATE DATABASE cybershield OWNER cybershield_user;
```

### 4. Create your `.env` file

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS / Linux:

```bash
cp .env.example .env
```

Generate a secret key:

```
python -c "import secrets; print(secrets.token_hex(32))"
```

Then edit `.env` and set:

```
SECRET_KEY=<paste the generated value>
DATABASE_URL=postgresql://cybershield_user:<your-password>@localhost:5432/cybershield
```

**Both values are required.**

- `SECRET_KEY` signs the session cookie and the CSRF tokens. If it is
  missing, the login and registration pages fail with
  `RuntimeError: A secret key is required to use CSRF.` Use a long random
  value (the command above), not a word or the placeholder from
  `.env.example`. Changing it logs every user out.
- `DATABASE_URL` must point at the database created in step 3. If the
  password contains `@`, `:`, `/`, `#` or `%`, percent-encode it in the
  URL (for example `@` becomes `%40`).

**Keeping `.env` safe**

- `.env` is listed in `.gitignore`. Never commit it, and never copy it
  into a ZIP, report or shared folder. `.env.example` is the only
  version that belongs in the repository.
- Close the `.env` tab before taking screenshots or sharing your screen.
- If a key or password is ever exposed (screenshot, chat, email, commit),
  treat it as compromised: generate a new `SECRET_KEY`, and change the
  database password with
  `ALTER ROLE cybershield_user WITH PASSWORD '<new-password>';` in
  `psql`, then update `.env`.

### 5. Create the database tables

The migration is already committed in `migrations/`, so only apply it:

```
flask --app run.py db upgrade
```

Do **not** run `flask db init` or `flask db migrate` for setup. `init`
fails because `migrations/` already exists, and `migrate` is only for
developers who have changed a model and need to generate a new
migration.

To check which migration is applied: `flask --app run.py db current`.
To remove the application tables again (this deletes all data):
`flask --app run.py db downgrade base`.

### 6. Load the training scenarios

```
python seed.py
```

This inserts the six scenarios. It is safe to re-run: scenarios are
matched by title, so a second run updates them (picking up edits to
`app/seed_data.py`) instead of creating duplicates.

### 7. Create an admin account

```
python create_admin.py
```

You'll be prompted for an email, name, and password (hidden input,
via `getpass` — never a CLI argument, never hard-coded). If the email
already belongs to an existing regular user, the script offers to
promote that account to admin instead of creating a duplicate.

### 8. Run the application

```
python run.py
```

The app runs at `http://127.0.0.1:5000` (change the port with `PORT` in
`.env`). Visit `/register` to create a learner account, log in at
`/login`, then go to `/training` to start a scenario. Admin pages are
under `/admin/`. Stop the server with Ctrl+C.

This is Flask's development server, intended for local demonstration
only.

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
| `/admin/analytics` | GET | Admin only | Category/difficulty breakdown + phishing analyzer library report |
| `/admin/users` | GET | Admin only | List all registered users (no password hashes) |
| `/admin/users/<id>` | GET | Admin only | One user's full progress + history |
| `/admin/results` | GET | Admin only | Every user's every training attempt |
| `/admin/results/export.csv` | GET | Admin only | CSV download of every recorded response |
| `/admin/scenarios` | GET | Admin only | Per-scenario attempt count / accuracy |

## Running the tests

Tests run against an in-memory SQLite database by default (see
`TestingConfig` in `app/config.py`), so neither PostgreSQL nor a `.env`
file is needed to run them:

```
python -m pytest -v
```

All 68 tests should pass, with no warnings:

| File | Tests | Covers |
|---|---|---|
| `test_auth.py` | 7 | registration, password hashing, duplicate email, login, dashboard access |
| `test_training.py` | 11 | scenario display, submission, scoring, results isolation, feedback analysis |
| `test_admin.py` | 14 | admin access control, analytics, user detail, CSV export |
| `test_phishing_analyzer.py` | 4 | each indicator type and the no-indicator case |
| `test_attempt_rules.py` | 15 | one attempt per scenario, duplicate submissions, feedback without an attempt, inactive scenarios |
| `test_csrf.py` | 7 | POSTs rejected without a valid CSRF token, accepted with one |
| `test_seed_and_migration.py` | 7 | seed data shape, seed idempotence, migration upgrade/downgrade |
| `test_session_loading.py` | 3 | user reloaded from the session cookie, deleted user, logout |

### Saving test and coverage output as evidence

```
python scripts/save_test_evidence.py
```

This runs the whole suite with coverage and writes everything pytest
prints to `evidence/test-output/pytest_<date>_<time>.txt`, with a header
recording the date, git commit, Python version, operating system and
database backend. It records only the backend *name* (for example
`sqlite` or `postgresql`), never the connection string, and it does not
read `.env`.

The equivalent manual command is:

```
python -m pytest -v -p no:cacheprovider --cov=app --cov-report=term-missing
```

### Running the tests against PostgreSQL (optional)

Create a separate, empty database for testing — the tests create and
drop every table, so **never point this at the database that holds your
real data**:

```sql
CREATE DATABASE cybershield_test OWNER cybershield_user;
```

Set `TEST_DATABASE_URL` for the current terminal only, then run the
tests.

Windows PowerShell:

```powershell
$env:TEST_DATABASE_URL = "postgresql://cybershield_user:<your-password>@localhost:5432/cybershield_test"
python -m pytest -v
Remove-Item Env:TEST_DATABASE_URL
```

macOS / Linux:

```bash
TEST_DATABASE_URL="postgresql://cybershield_user:<your-password>@localhost:5432/cybershield_test" python -m pytest -v
```

The seed and migration tests always use a temporary SQLite file,
whatever `TEST_DATABASE_URL` is set to.

## Dependency licences

Third-party packages installed from `requirements.txt`, with the
licence each declares in its package metadata. No licence has been
chosen for the CyberShield code itself.

| Package | Version | Licence |
|---|---|---|
| Flask | 3.0.3 | BSD-3-Clause |
| Flask-SQLAlchemy | 3.1.1 | BSD-3-Clause |
| SQLAlchemy | 2.0.52 | MIT |
| Flask-Migrate | 4.0.7 | MIT |
| Flask-Login | 0.6.3 | MIT |
| Flask-WTF | 1.2.1 | BSD-3-Clause |
| WTForms | 3.1.2 | BSD-3-Clause |
| email-validator | 2.1.1 | The Unlicense |
| python-dotenv | 1.0.1 | BSD-3-Clause |
| psycopg2-binary | 2.9.10 | LGPL with exceptions |
| pytest | 8.2.2 | MIT |
| pytest-cov | 7.1.0 | MIT |

PostgreSQL itself is released under the PostgreSQL Licence.

## Environment variables reference

| Variable          | Purpose                                              |
|-------------------|-------------------------------------------------------|
| `FLASK_CONFIG`    | `development`, `production`, or `testing`             |
| `SECRET_KEY`      | **Required.** Flask session/CSRF signing key — never commit a real one |
| `DATABASE_URL`    | **Required.** PostgreSQL connection string            |
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
8. Admin functionality *(Stage 3)*
9. Testing (expanded) *(Stage 2, 3 & 4)*
10. Documentation/UI improvements — ongoing
11. Admin analytics, phishing analyzer integration, CSV reporting *(Stage 4)*
12. QA hardening: additional tests, deprecation fixes, dependency pin, setup documentation *(Stage 5)*
