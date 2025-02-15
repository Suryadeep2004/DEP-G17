from flask import Blueprint, render_template

faculty_bp = Blueprint("faculty", __name__)

@faculty_bp.route("/faculty")
def profile():
    email = "email@example.com"
    return render_template("faculty/profile.html", email=email)