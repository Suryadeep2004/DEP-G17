from flask import Blueprint, render_template, session, redirect, url_for

caretaker_bp = Blueprint("caretaker", __name__)

@caretaker_bp.route("/caretaker")
def profile():
    if 'user_id' not in session or session.get('user_role') != 'caretaker':
        return redirect(url_for('auth.login'))
    email = "email@example.com"  # Replace with actual email from session or database
    return render_template("caretaker/profile.html", email=email)