from flask import Blueprint, render_template

student_bp = Blueprint("student", __name__)

@student_bp.route("/student")
def profile():
    email = "email@example.com"
    return render_template("student/profile.html", email=email)