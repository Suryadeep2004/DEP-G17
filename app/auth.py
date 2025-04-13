from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import CustomUser, Student, Caretaker, Faculty, Admin, Warden, Guest
from app.database import db
from flask_mail import Message
from app import mail
import random
import time

auth_bp = Blueprint("auth", __name__)

otp_generated = False
otp_value = None
otp_timestamp = None

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
        elif user_role == 'guest':
            return redirect(url_for("guest.profile"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = CustomUser.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash("Your account is not verified yet. Please contact the administrator.", "warning")
                return redirect(url_for("auth.login"))
            
            session['user_id'] = user.id
            session['user_name'] = user.name  
            session['user_email'] = user.email  
            if Student.query.filter_by(student_id=user.id).first():
                session['user_role'] = 'student'
                return redirect(url_for("student.profile"))
            elif Caretaker.query.filter_by(user_id=user.id).first():
                session['user_role'] = 'caretaker'
                return redirect(url_for("caretaker.profile"))
            elif Faculty.query.filter_by(faculty_id=user.id).first():
                faculty = Faculty.query.filter_by(faculty_id=user.id).first()
                session['user_role'] = 'faculty'
                session['is_hod'] = faculty.is_hod
                warden = Warden.query.filter_by(faculty_id=user.id).first()
                session['is_chief_warden'] = warden.is_chief if warden else False
                return redirect(url_for("faculty.profile"))
            elif Admin.query.filter_by(admin_id=user.id).first():
                admin = Admin.query.filter_by(admin_id=user.id).first()
                session['user_role'] = 'admin'
                session['designation'] = admin.designation 
                return redirect(url_for("admin.profile"))
            elif Guest.query.filter_by(guest_id=user.id).first():
                session['user_role'] = 'guest'
                print("Redirecting to guest profile")  # Debug statement
                return redirect(url_for("guest.profile"))
            
            flash("Login successful!", "success")
        else:
            flash("Invalid credentials", "danger")
    return render_template("auth/login.html", title="Login")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    global otp_generated, otp_value, otp_timestamp

    if request.method == "POST":
        if 'generate_otp' in request.form:
            name = request.form.get("name")
            email = request.form.get("email")
            password = request.form.get("password")

            # Check if the email is already registered
            if CustomUser.query.filter_by(email=email).first():
                flash("Email is already registered. Please use a different email.", "warning")
                return render_template("auth/register.html", otp_generated=otp_generated)

            # Save user details in the session
            session['name'] = name
            session['email'] = email
            session['password'] = password

            # Generate OTP
            otp_value = random.randint(100000, 999999)
            otp_generated = True
            otp_timestamp = time.time()

            # Send OTP via email
            msg = Message("Your OTP for Hostel Management System", sender="johnDoe18262117@gmail.com", recipients=[email])
            msg.body = f"Your OTP is {otp_value}. It will expire in 5 minutes."
            mail.send(msg)

            flash("OTP has been sent to your email.", "info")
            return render_template("auth/register.html", otp_generated=otp_generated)

        elif 'verify_otp' in request.form:
            otp_input = request.form.get("otp")

            # Validate OTP format
            if not otp_input.isdigit() or len(otp_input) != 6:
                flash("Invalid OTP format. Please enter a 6-digit number.", "danger")
                return render_template("auth/register.html", otp_generated=otp_generated)

            # Verify OTP and expiration
            if otp_value and otp_input and int(otp_input) == otp_value and (time.time() - otp_timestamp) < 300:
                name = session.get('name')
                email = session.get('email')
                password = session.get('password')

                # Create a new user
                new_user = CustomUser(name=name, email=email, password=password)
                db.session.add(new_user)
                db.session.commit()

                # Check email type and create appropriate user role
                if email.endswith("@iitrpr.ac.in"):
                    new_student = Student(student_id=new_user.id)
                    db.session.add(new_student)
                    session['user_role'] = 'student'
                    redirect_url = url_for("student.profile")
                else:
                    new_guest = Guest(guest_id=new_user.id)
                    db.session.add(new_guest)
                    session['user_role'] = 'guest'
                    redirect_url = url_for("guest.profile")

                db.session.commit()

                # Clear OTP and session data
                otp_generated = False
                otp_value = None
                otp_timestamp = None
                session.pop('name', None)
                session.pop('email', None)
                session.pop('password', None)

                flash("Registration successful! Redirecting to your dashboard.", "success")
                session['user_id'] = new_user.id
                return redirect(redirect_url)
            else:
                otp_generated = False
                otp_value = None
                otp_timestamp = None
                flash("Invalid or expired OTP. Please try again.", "danger")
                return render_template("auth/register.html", otp_generated=otp_generated)

    return render_template("auth/register.html", otp_generated=otp_generated)

@auth_bp.route("/logout")
def logout():
    session.clear()  # Clear all session variables
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))