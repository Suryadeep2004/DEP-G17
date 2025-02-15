from flask import Blueprint, render_template, request, redirect, url_for, flash

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "password": 
            flash("Login successful!", "success")
            return redirect(url_for("index.home"))
        else:
            flash("Invalid credentials", "danger")
    return render_template("auth/login.html", title="Login")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if password == confirm_password: 
            flash("Registration successful!", "success")
            return redirect(url_for("auth.login"))
        else:
            flash("Passwords do not match", "danger")
    return render_template("auth/register.html", title="Register")