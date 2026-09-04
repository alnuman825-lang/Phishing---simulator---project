"""
Scenario model.

Represents one simulated phishing training scenario. All content here
is fictional training material — no real sender addresses, no real
organisations impersonated without a clear "SIMULATION" label, and no
functional links.

NOTE: This model is defined in Stage 1 so the database schema is
complete from the first migration. The routes/logic for serving
scenarios and grading responses are implemented in Stage 2.
"""

from app.extensions import db


class Scenario(db.Model):
    __tablename__ = "scenarios"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    sender_name = db.Column(db.String(150), nullable=False)
    sender_email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    context = db.Column(db.Text, nullable=True)
    explanation = db.Column(db.Text, nullable=False)  # shown after response
    correct_response = db.Column(db.String(20), nullable=False)  # click | report | ignore
    difficulty = db.Column(db.String(20), nullable=False, default="beginner")
    category = db.Column(db.String(50), nullable=False, default="general")
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    responses = db.relationship(
        "Response", backref="scenario", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Scenario {self.id}: {self.title}>"
