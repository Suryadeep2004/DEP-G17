from flask import Blueprint, render_template, session, redirect, url_for
from app.models import CustomUser, Student

student_bp = Blueprint("student", __name__)

@student_bp.route("/student", methods=["GET"])
def profile():
    # Redirect if not a student or not logged in
    if session.get('user_role') != 'student' or 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = CustomUser.query.get(user_id)
    student = Student.query.get(user_id) 

    if not user or not student:
        return redirect(url_for('auth.login'))

    return render_template("student/profile.html", user=user, student=student)