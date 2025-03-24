from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models import Admin, CustomUser
from app import mail
from flask_mail import Message
import random

index_bp = Blueprint("index", __name__)

@index_bp.route("/")
def home():
    return render_template("basic/index.html", title="Hostel Management System")

@index_bp.route("/about")
def about():
    return render_template("basic/about.html", title="About Us")

@index_bp.route("/contact")
def contact():
    return render_template("basic/contact.html", title="Contact Us")

@index_bp.route("/contact_us", methods=["POST"])
def contact_us():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    if not name or not email or not message:
        flash("All fields are required.", "danger")
        return redirect(url_for('index.contact'))

    # Get a random admin
    admins = Admin.query.all()
    if not admins:
        flash("No admin available to receive the message.", "danger")
        return redirect(url_for('index.contact'))

    admin = random.choice(admins)
    admin_user = CustomUser.query.get(admin.admin_id)

    # Send email to the random admin
    msg = Message(
        "New Contact Us Query",
        sender="your-email@example.com",  # Replace with your email
        recipients=[admin_user.email]
    )
    msg.body = f"Name: {name}\nEmail: {email}\nMessage: {message}"
    mail.send(msg)

    flash("Your message has been sent successfully.", "success")
    return redirect(url_for('index.contact'))