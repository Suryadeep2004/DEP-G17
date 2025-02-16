from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import CustomUser, Student, Caretaker, Faculty, Admin
from app.database import db

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if 'user_id' in session:
        user_role = session.get('user_role')
        if user_role == 'student':
            return redirect(url_for("student.profile"))
        elif user_role == 'caretaker':
            return redirect(url_for("caretaker.profile"))
        elif user_role == 'faculty':
            return redirect(url_for("faculty.profile"))
        elif user_role == 'admin':
            return redirect(url_for("admin.profile"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = CustomUser.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash("Your account is not verified yet. Please contact the administrator.", "warning")
                return redirect(url_for("auth.login"))
            
            session['user_id'] = user.id
            
            if Student.query.filter_by(student_id=user.id).first():
                session['user_role'] = 'student'
                return redirect(url_for("student.profile"))
            elif Caretaker.query.filter_by(user_id=user.id).first():
                session['user_role'] = 'caretaker'
                return redirect(url_for("caretaker.profile"))
            elif Faculty.query.filter_by(faculty_id=user.id).first():
                session['user_role'] = 'faculty'
                return redirect(url_for("faculty.profile"))
            elif Admin.query.filter_by(admin_id=user.id).first():
                session['user_role'] = 'admin'
                return redirect(url_for("admin.profile"))
            
            flash("Login successful!", "success")
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
            hashed_password = generate_password_hash(password, method='sha256')
            new_user = CustomUser(name=name, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful!", "success")
            return redirect(url_for("auth.login"))
        else:
            flash("Passwords do not match", "danger")
    return render_template("auth/register.html", title="Register")

@auth_bp.route("/logout")
def logout():
    session.pop('user_id', None)
    session.pop('user_role', None)
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))