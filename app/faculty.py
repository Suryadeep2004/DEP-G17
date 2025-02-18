from flask import Blueprint, render_template, session, redirect, url_for
from app.models import CustomUser, Faculty

faculty_bp = Blueprint("faculty", __name__)

@faculty_bp.route("/faculty", methods=["GET"])
def profile():
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = CustomUser.query.get(user_id)
    faculty = Faculty.query.filter_by(faculty_id=user_id).first()

    if user is None or faculty is None:
        return redirect(url_for('auth.login'))

    return render_template("faculty/profile.html", user=user, faculty=faculty)