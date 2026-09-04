"""
Authorization helpers.

Separate from Flask-Login's @login_required, which only checks that
*someone* is logged in. @admin_required additionally checks the
role, and is deliberately placed after @login_required in route
decorator stacks so an anonymous user gets redirected to /login
(the expected UX) rather than a bare 403.
"""

from functools import wraps

from flask import abort
from flask_login import current_user


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped
