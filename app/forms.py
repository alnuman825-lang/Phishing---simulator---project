"""
Form definitions (Flask-WTF).

Using WTForms gives us server-side validation and automatic CSRF
tokens on every form, satisfying the "server-side validation" and
"CSRF protection" security requirements.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError

from app.models.user import User


class RegistrationForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters.")],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create account")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")
