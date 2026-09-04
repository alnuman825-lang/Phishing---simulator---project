"""
Response model.

Records a single user's answer to a single scenario. Grading logic
(is_correct, score) is computed in Stage 2's response-submission
route, not here — the model just stores the outcome.
"""

from datetime import datetime, timezone

from app.extensions import db


class Response(db.Model):
    __tablename__ = "responses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    scenario_id = db.Column(db.Integer, db.ForeignKey("scenarios.id"), nullable=False)
    selected_response = db.Column(db.String(20), nullable=False)  # click | report | ignore
    is_correct = db.Column(db.Boolean, nullable=False)
    score = db.Column(db.Integer, nullable=False, default=0)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "scenario_id", name="uq_user_scenario"),
    )

    def __repr__(self) -> str:
        return f"<Response user={self.user_id} scenario={self.scenario_id} correct={self.is_correct}>"
