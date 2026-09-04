"""
Dashboard routes.

Stage 2 update: stats now include total available scenarios,
incorrect count, and a completed/total progress figure, all computed
from the database -- nothing hard-coded.
"""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from app.models.response import Response
from app.models.scenario import Scenario

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def root():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))


@dashboard_bp.route("/dashboard")
@login_required
def index():
    user_responses = Response.query.filter_by(user_id=current_user.id).all()
    total_scenarios = Scenario.query.filter_by(is_active=True).count()

    scenarios_completed = len(user_responses)
    correct_count = sum(1 for r in user_responses if r.is_correct)
    incorrect_count = scenarios_completed - correct_count
    total_score = sum(r.score for r in user_responses)
    max_possible_score = scenarios_completed * 100
    accuracy = round((correct_count / scenarios_completed) * 100, 1) if scenarios_completed else 0.0

    stats = {
        "scenarios_completed": scenarios_completed,
        "total_scenarios": total_scenarios,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "total_score": total_score,
        "max_possible_score": max_possible_score,
        "accuracy": accuracy,
    }

    return render_template("dashboard.html", stats=stats)
