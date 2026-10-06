"""
Admin routes.

Every route here requires an authenticated admin (see app/authz.py).
Read-only by design — admins can inspect users, results, and
performance analytics, but cannot edit or delete anything from these
views. Plaintext passwords are never accessible: the User model
doesn't even expose one (only password_hash, which is not rendered
anywhere in these templates).
"""

import csv
import io
from collections import defaultdict

from flask import Blueprint, render_template, Response as FlaskResponse
from flask_login import login_required

from app.authz import admin_required
from app.extensions import db
from app.models.user import User
from app.models.scenario import Scenario
from app.models.response import Response
from app.services.phishing_analyzer import PhishingAnalyzer

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _scenario_attempt_stats(scenario, all_responses_by_scenario):
    """Attempt/correctness stats for one scenario, from a preloaded map."""
    attempts = all_responses_by_scenario.get(scenario.id, [])
    attempt_count = len(attempts)
    correct_count = sum(1 for r in attempts if r.is_correct)
    incorrect_count = attempt_count - correct_count
    accuracy = round((correct_count / attempt_count) * 100, 1) if attempt_count else 0.0
    return attempt_count, correct_count, incorrect_count, accuracy


@admin_bp.route("/")
@login_required
@admin_required
def overview():
    total_users = User.query.count()
    total_scenarios = Scenario.query.filter_by(is_active=True).count()
    total_responses = Response.query.count()
    total_correct = Response.query.filter_by(is_correct=True).count()
    overall_accuracy = round(
        (total_correct / total_responses) * 100, 1) if total_responses else 0.0

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


@admin_bp.route("/users/<int:user_id>")
@login_required
@admin_required
def user_detail(user_id):
    """Per-user drill-down: one user's full training history and progress,
    the same way the user sees their own dashboard/results, but for admins
    reviewing a specific person's performance."""
    target_user = db.get_or_404(User, user_id)

    rows = (
        db.session.query(Response, Scenario)
        .join(Scenario, Response.scenario_id == Scenario.id)
        .filter(Response.user_id == target_user.id)
        .order_by(Response.submitted_at.desc())
        .all()
    )

    total_scenarios = Scenario.query.filter_by(is_active=True).count()
    completed = len(rows)
    correct = sum(1 for response, _ in rows if response.is_correct)
    incorrect = completed - correct
    total_score = sum(response.score for response, _ in rows)
    accuracy = round((correct / completed) * 100, 1) if completed else 0.0

    stats = {
        "scenarios_completed": completed,
        "total_scenarios": total_scenarios,
        "correct_count": correct,
        "incorrect_count": incorrect,
        "accuracy": accuracy,
        "total_score": total_score,
        "max_possible_score": completed * 100,
    }

    return render_template(
        "admin/user_detail.html", target_user=target_user, stats=stats, rows=rows
    )


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


@admin_bp.route("/results/export.csv")
@login_required
@admin_required
def export_results_csv():
    """Download every recorded response as CSV — the 'Reporting' deliverable
    called for in the project brief, on top of the in-browser results table."""
    rows = (
        db.session.query(Response, User, Scenario)
        .join(User, Response.user_id == User.id)
        .join(Scenario, Response.scenario_id == Scenario.id)
        .order_by(Response.submitted_at.desc())
        .all()
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "user_name", "user_email", "scenario_title", "category", "difficulty",
        "selected_response", "correct_response", "is_correct", "score", "submitted_at",
    ])
    for response, user, scenario in rows:
        writer.writerow([
            user.name,
            user.email,
            scenario.title,
            scenario.category,
            scenario.difficulty,
            response.selected_response,
            scenario.correct_response,
            response.is_correct,
            response.score,
            response.submitted_at.isoformat() if response.submitted_at else "",
        ])

    csv_data = buffer.getvalue()
    return FlaskResponse(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=cybershield_results.csv"},
    )


@admin_bp.route("/scenarios")
@login_required
@admin_required
def scenarios():
    scenario_stats = []
    all_responses = Response.query.all()
    by_scenario = defaultdict(list)
    for r in all_responses:
        by_scenario[r.scenario_id].append(r)

    for scenario in Scenario.query.order_by(Scenario.id).all():
        attempt_count, correct_count, _, accuracy = _scenario_attempt_stats(scenario, by_scenario)
        scenario_stats.append({
            "scenario": scenario,
            "attempt_count": attempt_count,
            "correct_count": correct_count,
            "accuracy": accuracy,
        })
    return render_template("admin/scenarios.html", scenario_stats=scenario_stats)


@admin_bp.route("/analytics")
@login_required
@admin_required
def analytics():
    """Performance analytics beyond the single-scenario breakdown on
    /admin/scenarios: results grouped by category and by difficulty, plus
    the rule-based phishing indicator analysis applied across the whole
    active scenario library (not just at attempt-feedback time) so admins
    can see which indicator types the training content actually covers.
    """
    all_responses = Response.query.all()
    by_scenario = defaultdict(list)
    for r in all_responses:
        by_scenario[r.scenario_id].append(r)

    active_scenarios = Scenario.query.filter_by(is_active=True).order_by(Scenario.id).all()

    # --- Per-scenario stats + indicator analysis (integrates PhishingAnalyzer) ---
    analyzer = PhishingAnalyzer()
    scenario_analytics = []
    risk_level_counts = {"high": 0, "medium": 0, "low": 0}
    indicator_counts = defaultdict(int)
    total_risk_score = 0

    for scenario in active_scenarios:
        attempt_count, correct_count, incorrect_count, accuracy = _scenario_attempt_stats(
            scenario, by_scenario
        )
        analysis = analyzer.analyze(f"{scenario.subject}\n{scenario.body}")
        risk_level_counts[analysis["risk_level"]] = risk_level_counts.get(analysis["risk_level"], 0) + 1
        total_risk_score += analysis["risk_score"]
        for finding in analysis["findings"]:
            indicator_counts[finding["indicator"]] += 1

        scenario_analytics.append({
            "scenario": scenario,
            "attempt_count": attempt_count,
            "correct_count": correct_count,
            "incorrect_count": incorrect_count,
            "accuracy": accuracy,
            "risk_level": analysis["risk_level"],
            "risk_score": analysis["risk_score"],
        })

    avg_risk_score = round(total_risk_score / len(active_scenarios), 1) if active_scenarios else 0.0

    # --- Category breakdown ---
    category_totals = defaultdict(lambda: {"attempts": 0, "correct": 0})
    difficulty_totals = defaultdict(lambda: {"attempts": 0, "correct": 0})

    for scenario in Scenario.query.all():
        for response in by_scenario.get(scenario.id, []):
            category_totals[scenario.category]["attempts"] += 1
            difficulty_totals[scenario.difficulty]["attempts"] += 1
            if response.is_correct:
                category_totals[scenario.category]["correct"] += 1
                difficulty_totals[scenario.difficulty]["correct"] += 1

    def _to_breakdown(totals):
        breakdown = []
        for key, values in sorted(totals.items()):
            attempts = values["attempts"]
            correct = values["correct"]
            accuracy = round((correct / attempts) * 100, 1) if attempts else 0.0
            breakdown.append({"label": key, "attempts": attempts, "correct": correct, "accuracy": accuracy})
        return breakdown

    category_breakdown = _to_breakdown(category_totals)
    difficulty_breakdown = _to_breakdown(difficulty_totals)

    # Sort indicators by how many active scenarios trigger them, most first
    indicator_breakdown = sorted(indicator_counts.items(), key=lambda kv: kv[1], reverse=True)

    return render_template(
        "admin/analytics.html",
        scenario_analytics=scenario_analytics,
        category_breakdown=category_breakdown,
        difficulty_breakdown=difficulty_breakdown,
        indicator_breakdown=indicator_breakdown,
        risk_level_counts=risk_level_counts,
        avg_risk_score=avg_risk_score,
        total_active_scenarios=len(active_scenarios),
    )
