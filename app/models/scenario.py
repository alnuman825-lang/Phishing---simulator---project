from app.extensions import db


class Scenario(db.Model):
    __tablename__ = "scenarios"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False, default="beginner")
    content = db.Column(db.Text, nullable=False)
    correct_response = db.Column(db.String(20), nullable=False)
    explanation = db.Column(db.Text, nullable=False)

    responses = db.relationship(
        "Response",
        back_populates="scenario",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Scenario {self.id}: {self.title}>"
