"""
Admin routes.

Every route here requires an authenticated admin (see app/authz.py).
Deliberately read-only for Stage 3 — admins can inspect users,
results, and scenario performance, but cannot edit or delete
anything yet. Plaintext passwords are never accessible: the User
model doesn't even expose one (only password_hash, which is not
rendered anywhere in these templates).
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.authz import admin_required
from app.extensions import db
from app.models.user import User
from app.models.scenario import Scenario
from app.models.response import Response

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@admin_required
def overview():
    total_users = User.query.count()
    total_scenarios = Scenario.query.filter_by(is_active=True).count()
    total_responses = Response.query.count()
    total_correct = Response.query.filter_by(is_correct=True).count()
    overall_accuracy = round((total_correct / total_responses) * 100, 1) if total_responses else 0.0

    stats = {
        "total_users": total_users,
        "total_scenarios": total_scenarios,
        "total_responses": total_responses,
        "total_correct": total_correct,
        "overall_accuracy": overall_accuracy,
    }
    return render_template("admin/overview.html", stats=stats)


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    # Only non-sensitive columns are selected/rendered — password_hash
    # is on the model but is never passed to the template context here.
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/results")
@login_required
@admin_required
def results():
    rows = (
        db.session.query(Response, User, Scenario)
        .join(User, Response.user_id == User.id)
        .join(Scenario, Response.scenario_id == Scenario.id)
        .order_by(Response.submitted_at.desc())
        .all()
    )
    return render_template("admin/results.html", rows=rows)


@admin_bp.route("/scenarios")
@login_required
@admin_required
def scenarios():
    scenario_stats = []
    for scenario in Scenario.query.order_by(Scenario.id).all():
        attempts = Response.query.filter_by(scenario_id=scenario.id).all()
        attempt_count = len(attempts)
        correct_count = sum(1 for r in attempts if r.is_correct)
        accuracy = round((correct_count / attempt_count) * 100, 1) if attempt_count else 0.0
        scenario_stats.append({
            "scenario": scenario,
            "attempt_count": attempt_count,
            "correct_count": correct_count,
            "accuracy": accuracy,
        })
    return render_template("admin/scenarios.html", scenario_stats=scenario_stats)
