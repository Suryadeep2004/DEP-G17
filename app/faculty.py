from flask import Blueprint, render_template, session, redirect, url_for

faculty_bp = Blueprint("faculty", __name__)

@faculty_bp.route("/faculty")
def profile():
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))
    email = "email@example.com"  # Replace with actual email from session or database
    return render_template("faculty/profile.html", email=email)