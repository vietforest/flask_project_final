from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def admin_required(view):
    """Like @login_required, but the user must also be an admin (otherwise 403 Forbidden)."""
    @wraps(view)
    @login_required                      # not logged in -> redirect to the login page
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:    # logged in but not admin -> 403
            abort(403)
        return view(*args, **kwargs)
    return wrapped