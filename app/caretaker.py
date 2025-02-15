from flask import Blueprint, render_template

caretaker_bp = Blueprint("caretaker", __name__)

@caretaker_bp.route("/caretaker")
def profile():
    email = "email@example.com"
    return render_template("caretaker/profile.html", email=email)