from flask import Blueprint, render_template, session, redirect, url_for, request, flash, send_file, send_from_directory, jsonify
from app.models import CustomUser, Student, InternshipApplication, Faculty, Admin, db, Caretaker, Room, Hostel, RoomChangeRequest, GuestRoomBooking, Warden, ProjectAccommodationRequest, Guest, Notification
from werkzeug.utils import secure_filename
from flask_mail import Message
from app import mail  
import os
from datetime import datetime
from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet 
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch
from sqlalchemy.sql import func
from random import randint

guest_bp = Blueprint("guest", __name__)

@guest_bp.route("/guest", methods=["GET"])
def profile():
    if 'user_id' not in session or session.get('user_role') != 'guest':
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = CustomUser.query.get(user_id)
    guest = Guest.query.filter_by(guest_id=user_id).first()

    # Fetch all notifications for the user
    notifications = Notification.query.filter_by(recipient_email=user.email).order_by(Notification.timestamp.desc()).all()

    # Fetch only unread notifications for the badge count
    unread_notifications_count = Notification.query.filter_by(recipient_email=user.email, is_read=False).count()

    if user is None or guest is None:
        return redirect(url_for('auth.login'))

    return render_template(
        "guest/profile.html",
        user=user,
        guest=guest,
        notifications=notifications,
        unread_notifications_count=unread_notifications_count
    )

@guest_bp.route("/guest/mark-notifications-read", methods=["POST"])
def mark_notifications_read():
    if 'user_id' not in session or session.get('user_role') != 'guest':
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    user = CustomUser.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Mark all notifications as read for the current user
    notifications = Notification.query.filter_by(recipient_email=user.email, is_read=False).all()
    for notification in notifications:
        notification.is_read = True

    db.session.commit()
    return jsonify({'success': True}), 200

@guest_bp.route("/guest/update_profile", methods=["GET", "POST"])
def update_profile():
    if 'user_id' not in session or session.get('user_role') != 'guest':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    user = CustomUser.query.get(user_id)
    guest = Guest.query.filter_by(guest_id=user_id).first()

    if request.method == "POST":
        # Get updated data from the form
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')

        # Update the database
        user.name = name
        user.email = email
        guest.phone = phone
        guest.address = address

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for('guest.profile'))

    return render_template("guest/update_profile.html", user=user, guest=guest)

@guest_bp.route("/guest_room_booking_form", methods=["GET"])
def guest_room_booking_form():
    if 'user_id' not in session or session.get('user_role') != 'guest':
        return redirect(url_for('auth.login'))

    return render_template("guest/guest_room_booking_form.html")

@guest_bp.route("/guest/submit_guest_room_booking", methods=["POST"])
def submit_guest_room_booking():
    if 'user_id' not in session or session.get('user_role') != 'guest':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    total_guests = request.form.get('total_guests')
    guests_male = request.form.get('guests_male')
    guests_female = request.form.get('guests_female')
    guest_names = request.form.get('guest_names')
    relation_with_applicant = request.form.get('relation_with_applicant')
    guest_address = request.form.get('guest_address')
    guest_contact = request.form.get('guest_contact')
    guest_email = request.form.get('guest_email')
    purpose_of_visit = request.form.get('purpose_of_visit')
    room_category = request.form.get('room_category')
    date_arrival = request.form.get('date_arrival')
    time_arrival = request.form.get('time_arrival')
    date_departure = request.form.get('date_departure')
    time_departure = request.form.get('time_departure')
    accommodation_by = request.form.get('accommodation_by')
    remarks = request.form.get('remarks')

    # Convert date and time strings to Python date and time objects
    date_arrival = datetime.strptime(date_arrival, '%Y-%m-%d').date()
    time_arrival = datetime.strptime(time_arrival, '%H:%M').time()
    date_departure = datetime.strptime(date_departure, '%Y-%m-%d').date()
    time_departure = datetime.strptime(time_departure, '%H:%M').time()

    guest_room_booking = GuestRoomBooking(
        applicant_id=user_id,
        total_guests=total_guests,
        guests_male=guests_male,
        guests_female=guests_female,
        guest_names=guest_names,
        relation_with_applicant=relation_with_applicant,
        guest_address=guest_address,
        guest_contact=guest_contact,
        guest_email=guest_email,
        purpose_of_visit=purpose_of_visit,
        room_category=room_category,
        date_arrival=date_arrival,
        time_arrival=time_arrival,
        date_departure=date_departure,
        time_departure=time_departure,
        accommodation_by=accommodation_by,
        remarks=remarks,
        status='Awaiting Allocation from JA (HM)'
    )

    db.session.add(guest_room_booking)
    db.session.commit()

    flash("guest room booking application submitted successfully.", "success")
    return redirect(url_for('guest.profile'))


@guest_bp.route("/guest/view_guest_room_booking_pdf/<int:booking_id>", methods=["GET"])
def view_guest_room_booking_pdf(booking_id):
    if 'user_id' not in session or session.get('user_role') != 'guest':
        return redirect(url_for('auth.login'))

    booking = GuestRoomBooking.query.get(booking_id)
    if not booking:
        flash("No guest room booking application found.", "danger")
        return redirect(url_for('guest.profile'))

    template_path = "static/pdf formats/guest room booking form.pdf"

    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica", 10)

    # --- Fill Data on PDF ---
    can.drawString(70, 605, f"{booking.applicant.name}")  # Applicant name
    can.drawString(460, 605, f"{booking.guest_contact or 'N/A'}")  # guest contact
    can.drawString(350, 605, f"{booking.guest_email or 'N/A'}")  # guest email
    can.drawString(160, 605, "guest")  # Indicate the role as "guest"
    can.drawString(265, 605, f"{booking.guest_address or 'N/A'}")

    can.drawString(250, 560, f"{booking.guests_male}")
    can.drawString(300, 560, f"{booking.guests_female}")
    can.drawString(450, 560, f"{booking.total_guests}")
    can.drawString(235, 536, f"{booking.guest_names}")
    can.drawString(235, 512, f"{booking.relation_with_applicant}")
    can.drawString(235, 479, f"{booking.guest_address}")
    can.drawString(317, 443, f"{booking.guest_contact}")
    can.drawString(430, 443, f"{booking.guest_email or 'N/A'}")
    can.drawString(130, 420, f"{booking.purpose_of_visit}")

    # Room category
    if booking.room_category == "A":
        can.drawString(327, 407, "\u2713")
    else:
        can.drawString(390, 407, "\u2713")

    # Accommodation by
    if booking.accommodation_by == "guest":
        can.drawString(340, 257, "\u2713")
    else:
        can.drawString(420, 257, "\u2713")

    # Render date and time separately
    can.drawString(140, 350, f"{booking.date_arrival.strftime('%d')}")
    can.drawString(180, 350, f"{booking.date_arrival.strftime('%m')}")
    can.drawString(230, 350, f"{int(booking.date_arrival.strftime('%Y')) % 100}")
    can.drawString(360, 350, f"{booking.time_arrival.strftime('%H')}:{booking.time_arrival.strftime('%M')}")  # 24-hour format

    can.drawString(140 + 10, 315, f"{booking.date_departure.strftime('%d')}")
    can.drawString(180 + 10, 315, f"{booking.date_departure.strftime('%m')}")
    can.drawString(230 + 10, 315, f"{int(booking.date_departure.strftime('%Y')) % 100}")
    can.drawString(360, 315, f"{booking.time_departure.strftime('%H')}:{booking.time_departure.strftime('%M')}")  # 24-hour format

    can.drawString(125, 220, f"{booking.remarks or 'N/A'}")

    can.save()
    packet.seek(0)

    reader = PdfReader(template_path)
    writer = PdfWriter()
    overlay = PdfReader(packet)

    # Merge the overlay only with the first page of the template
    if len(reader.pages) > 0:
        first_page = reader.pages[0]
        first_page.merge_page(overlay.pages[0])
        writer.add_page(first_page)

    # Add the remaining pages of the template without modification
    for page in reader.pages[1:]:
        writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    output.seek(0)

    return send_file(
        output,
        mimetype="application/pdf",
        download_name="guest_room_booking_filled.pdf",
        as_attachment=False  # This ensures the PDF is displayed inline
    )


@guest_bp.route("/status", methods=["GET", "POST"])
def status():
    if 'user_id' not in session or session.get('user_role') != 'guest':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    filter_date = request.form.get('filter_date')  # Get the date from the form

    if filter_date:
        # Convert filter_date to a datetime.date object
        try:
            filter_date_obj = datetime.strptime(filter_date, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
            return redirect(url_for('guest.status'))

        # Filter guest room bookings by the selected date
        guest_room_bookings = GuestRoomBooking.query.filter_by(applicant_id=user_id).filter(
            func.date(GuestRoomBooking.created_at) == filter_date_obj
        ).all()
    else:
        # Fetch all guest room bookings if no date is provided
        guest_room_bookings = GuestRoomBooking.query.filter_by(applicant_id=user_id).all() 

    return render_template(
        "guest/status.html",
        guest_room_bookings=guest_room_bookings,
        filter_date=filter_date
    )

@guest_bp.route("/guest/fill_payment_details/<int:booking_id>", methods=["GET", "POST"])
def fill_payment_details(booking_id):
    if 'user_id' not in session or session.get('user_role') != 'guest':
        return redirect(url_for('auth.login'))

    booking = GuestRoomBooking.query.get(booking_id)
    if not booking or booking.applicant_id != session['user_id']:
        flash("Invalid booking or access denied.", "danger")
        return redirect(url_for('guest.status'))

    if request.method == "POST":
        # Collect form data
        email = request.form.get("email")
        name = request.form.get("name")
        designation = request.form.get("designation")
        mobile = request.form.get("mobile")
        hostel_name = request.form.get("hostel_name")
        amount_deposited = request.form.get("amount_deposited")
        room_rent_month = request.form.get("room_rent_month")
        year = request.form.get("year")
        date_of_deposit = request.form.get("date_of_deposit")
        utr_number = request.form.get("utr_number")
        component_of_amount = request.form.get("component_of_amount")
        email_confirmation = request.form.get("email_confirmation")
        declaration = request.form.get("declaration")

        # Handle file upload
        payment_proof = request.files["payment_proof"]
        if payment_proof:
            proof_filename = secure_filename(payment_proof.filename)
            payment_proof.save(os.path.join("uploads", proof_filename))
        else:
            proof_filename = None

        # Save payment details to the booking
        booking.payment_details = {
            "email": email,
            "name": name,
            "designation": designation,
            "mobile": mobile,
            "hostel_name": hostel_name,
            "amount_deposited": amount_deposited,
            "room_rent_month": room_rent_month,
            "year": year,
            "date_of_deposit": date_of_deposit,
            "utr_number": utr_number,
            "payment_proof": proof_filename,
            "component_of_amount": component_of_amount,
            "email_confirmation": email_confirmation,
            "declaration": declaration,
        }
        booking.status = "Awaiting Payment Verification from JA (HM)"
        db.session.commit()

        flash("Payment details submitted successfully. Awaiting final approval.", "success")
        return redirect(url_for('guest.status'))

    return render_template("guest/fill_payment_details.html", booking=booking)

@guest_bp.route("/guest/notifications", methods=["GET"])
def view_notifications():
    if 'user_id' not in session or session.get('user_role') != 'guest':
        return redirect(url_for('auth.login'))

    user_email = CustomUser.query.get(session['user_id']).email
    notifications = Notification.query.filter_by(recipient_email=user_email).order_by(Notification.timestamp.desc()).all()
    return render_template("guest/notifications.html", notifications=notifications)


@guest_bp.context_processor
def inject_guest_room_booking():
    if 'user_id' in session and session.get('user_role') == 'guest':
        user_id = session['user_id']
        guest_room_booking = GuestRoomBooking.query.filter_by(applicant_id=user_id, status="Awaiting Payment from Applicant").first()
        return {'guest_room_booking': guest_room_booking}
    return {'guest_room_booking': None}