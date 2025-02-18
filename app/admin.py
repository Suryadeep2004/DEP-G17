from flask import Blueprint, render_template, session, redirect, url_for
from app.models import CustomUser, Admin

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin", methods=["GET"])
def profile():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = CustomUser.query.get(user_id)
    admin = Admin.query.filter_by(admin_id=user_id).first()

    if user is None or admin is None:
        return redirect(url_for('auth.login'))

    return render_template("admin/profile.html", user=user, admin=admin)