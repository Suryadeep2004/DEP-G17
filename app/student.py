from flask import Blueprint, render_template, session, redirect, url_for

student_bp = Blueprint("student", __name__)

@student_bp.route("/student")
def profile():
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))
    email = "email@example.com"  
    return render_template("student/profile.html", email=email)