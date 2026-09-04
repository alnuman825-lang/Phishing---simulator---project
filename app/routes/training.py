"""
Training routes: the actual phishing simulation workflow.

Routes:
    GET  /training                    -> list active scenarios + status
    GET  /training/<scenario_id>       -> show scenario, response form
    POST /training/<scenario_id>       -> submit + grade a response
    GET  /training/<scenario_id>/feedback -> immediate feedback for THIS user's attempt
    GET  /results                      -> current user's full history

All routes require login. Scoring and correctness are always computed
server-side from app.models.scenario.Scenario.correct_response — the
client never sends (and the server never trusts) a score or
correctness value.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.scenario import Scenario
from app.models.response import Response

training_bp = Blueprint("training", __name__)

VALID_RESPONSES = {"click", "report", "ignore"}
FULL_SCORE = 100
ZERO_SCORE = 0


@training_bp.route("/training")
@login_required
def index():
    scenarios = Scenario.query.filter_by(is_active=True).order_by(Scenario.id).all()

    completed_ids = {
        r.scenario_id
        for r in Response.query.filter_by(user_id=current_user.id).all()
    }

    return render_template(
        "training_list.html",
        scenarios=scenarios,
        completed_ids=completed_ids,
    )


@training_bp.route("/training/<int:scenario_id>", methods=["GET", "POST"])
@login_required
def attempt(scenario_id):
    scenario = Scenario.query.filter_by(id=scenario_id, is_active=True).first_or_404()

    existing = Response.query.filter_by(
        user_id=current_user.id, scenario_id=scenario.id
    ).first()
    if existing:
        # Already attempted — don't allow a second attempt or re-showing
        # the form (which would just be a way to "practice" toward the
        # right answer). Send them straight to their own feedback.
        flash("You've already completed this scenario.", "info")
        return redirect(url_for("training.feedback", scenario_id=scenario.id))

    if request.method == "POST":
        selected = request.form.get("selected_response")

        if selected not in VALID_RESPONSES:
            flash("Please choose one of the three response options.", "danger")
            return render_template("training_scenario.html", scenario=scenario)

        is_correct = selected == scenario.correct_response
        score = FULL_SCORE if is_correct else ZERO_SCORE

        response = Response(
            user_id=current_user.id,
            scenario_id=scenario.id,
            selected_response=selected,
            is_correct=is_correct,
            score=score,
        )
        db.session.add(response)
        try:
            db.session.commit()
        except IntegrityError:
            # Race condition guard: the unique(user_id, scenario_id)
            # constraint caught a duplicate submission that slipped
            # past the check above (e.g. a double-click / resubmit).
            db.session.rollback()
            flash("You've already completed this scenario.", "info")

        return redirect(url_for("training.feedback", scenario_id=scenario.id))

    return render_template("training_scenario.html", scenario=scenario)


@training_bp.route("/training/<int:scenario_id>/feedback")
@login_required
def feedback(scenario_id):
    scenario = Scenario.query.get_or_404(scenario_id)

    response = Response.query.filter_by(
        user_id=current_user.id, scenario_id=scenario.id
    ).first()

    if response is None:
        flash("You haven't attempted that scenario yet.", "warning")
        return redirect(url_for("training.index"))

    return render_template("training_feedback.html", scenario=scenario, response=response)


@training_bp.route("/results")
@login_required
def results():
    # Scoped to current_user.id only — there is no response/user id in
    # the URL for anyone to tamper with, so this cannot leak another
    # user's results regardless of what a user guesses or edits in the URL.
    rows = (
        db.session.query(Response, Scenario)
        .join(Scenario, Response.scenario_id == Scenario.id)
        .filter(Response.user_id == current_user.id)
        .order_by(Response.submitted_at.desc())
        .all()
    )

    return render_template("results.html", rows=rows)
