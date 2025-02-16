from flask import Blueprint, render_template, session, redirect, url_for

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin")
def profile():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))
    email = "email@example.com"  # Replace with actual email from session or database
    return render_template("admin/profile.html", email=email)