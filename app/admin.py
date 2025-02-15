from flask import Blueprint, render_template

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin")
def profile():
    email = "email@example.com"
    return render_template("admin/profile.html", email=email)