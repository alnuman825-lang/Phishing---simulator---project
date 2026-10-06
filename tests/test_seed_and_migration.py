"""
Tests for the seed script and the committed database migration.

Both use a throwaway SQLite file under pytest's tmp_path. They never
read the project's .env file and never touch the development database:
`load_dotenv` is replaced with a no-op before seed.py is imported, and
the database URI is pointed at the temporary file.
"""

import contextlib
import importlib
import os
import sys

import pytest
import sqlalchemy as sa

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models.scenario import Scenario
from app.seed_data import SCENARIOS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRATIONS_DIR = os.path.join(PROJECT_ROOT, "migrations")
VALID_RESPONSES = {"click", "report", "ignore"}


@pytest.fixture()
def temp_db_uri(tmp_path, monkeypatch):
    """Point the testing configuration at a temporary SQLite file."""
    uri = "sqlite:///" + str(tmp_path / "cybershield_test.db").replace("\\", "/")
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", uri)
    monkeypatch.setenv("FLASK_CONFIG", "testing")
    return uri


@contextlib.contextmanager
def temp_app():
    """An app + app context on the temporary database, cleaned up afterwards."""
    app = create_app("testing")
    with app.app_context():
        try:
            yield app
        finally:
            db.session.remove()
            db.engine.dispose()


# --- Seed data ----------------------------------------------------------------

def test_seed_data_is_well_formed():
    titles = [s["title"] for s in SCENARIOS]

    assert len(SCENARIOS) == 6
    assert len(set(titles)) == len(titles), "seed.py matches on title, so titles must be unique"
    for scenario in SCENARIOS:
        assert scenario["correct_response"] in VALID_RESPONSES
        for field in ("sender_name", "sender_email", "subject", "body", "explanation"):
            assert scenario[field].strip()


# --- Seed script --------------------------------------------------------------

@pytest.fixture()
def seed_module(temp_db_uri, monkeypatch):
    """Import seed.py without letting it read .env, against an empty schema."""
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.syspath_prepend(PROJECT_ROOT)
    monkeypatch.delitem(sys.modules, "seed", raising=False)
    module = importlib.import_module("seed")

    # seed() builds its own app; remember each one so its database
    # connections can be closed when the test finishes.
    created_apps = []
    real_create_app = module.create_app

    def tracking_create_app(*args, **kwargs):
        app = real_create_app(*args, **kwargs)
        created_apps.append(app)
        return app

    monkeypatch.setattr(module, "create_app", tracking_create_app)

    with temp_app() as app:
        db.create_all()

    yield module

    for app in created_apps:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
    monkeypatch.delitem(sys.modules, "seed", raising=False)


def _scenario_count():
    with temp_app():
        return Scenario.query.count()


def test_seed_creates_all_scenarios(seed_module, capsys):
    seed_module.seed()

    assert _scenario_count() == len(SCENARIOS)
    assert f"{len(SCENARIOS)} created, 0 updated" in capsys.readouterr().out


def test_seed_is_idempotent(seed_module, capsys):
    seed_module.seed()
    seed_module.seed()
    seed_module.seed()

    assert _scenario_count() == len(SCENARIOS)
    assert f"0 created, {len(SCENARIOS)} updated" in capsys.readouterr().out


def test_seed_restores_edited_scenario_without_duplicating(seed_module):
    seed_module.seed()
    title = SCENARIOS[0]["title"]

    with temp_app():
        scenario = Scenario.query.filter_by(title=title).one()
        scenario.explanation = "Tampered explanation"
        db.session.commit()

    seed_module.seed()

    with temp_app():
        scenario = Scenario.query.filter_by(title=title).one()
        assert scenario.explanation == SCENARIOS[0]["explanation"]
        assert Scenario.query.count() == len(SCENARIOS)


# --- Migration ----------------------------------------------------------------

def _columns(inspector, table):
    return {column["name"] for column in inspector.get_columns(table)}


def test_migration_upgrade_creates_schema_matching_models(temp_db_uri):
    from flask_migrate import upgrade

    with temp_app():
        upgrade(directory=MIGRATIONS_DIR)
        inspector = sa.inspect(db.engine)

        tables = set(inspector.get_table_names())
        assert {"users", "scenarios", "responses"} <= tables

        # Every column the models declare must exist after the migration,
        # and the migration must not create columns the models don't know.
        for table_name, table in db.metadata.tables.items():
            assert _columns(inspector, table_name) == set(table.columns.keys())

        unique_names = {u["name"] for u in inspector.get_unique_constraints("responses")}
        assert "uq_user_scenario" in unique_names

        fk_targets = {fk["referred_table"] for fk in inspector.get_foreign_keys("responses")}
        assert fk_targets == {"users", "scenarios"}


def test_migration_downgrade_removes_application_tables(temp_db_uri):
    from flask_migrate import downgrade, upgrade

    with temp_app():
        upgrade(directory=MIGRATIONS_DIR)
        downgrade(directory=MIGRATIONS_DIR, revision="base")

        tables = set(sa.inspect(db.engine).get_table_names())
        assert not {"users", "scenarios", "responses"} & tables


def test_application_works_on_migrated_schema(temp_db_uri):
    """Register, log in and answer a scenario on a database built by the
    migration (every other test builds its schema with db.create_all())."""
    from flask_migrate import upgrade

    with temp_app() as app:
        upgrade(directory=MIGRATIONS_DIR)
        db.session.add(Scenario(**SCENARIOS[0]))
        db.session.commit()
        scenario_id = Scenario.query.one().id

        client = app.test_client()
        client.post("/register", data={
            "name": "Sam Test", "email": "sam@example.com",
            "password": "password123", "confirm_password": "password123",
        })
        client.post("/login", data={"email": "sam@example.com", "password": "password123"})
        resp = client.post(f"/training/{scenario_id}", data={"selected_response": "report"})

        assert resp.status_code == 302
        assert client.get(f"/training/{scenario_id}/feedback").status_code == 200
