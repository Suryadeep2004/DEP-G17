from flask import Blueprint, render_template, session, redirect, url_for, request, flash, send_file, send_from_directory
from app.models import CustomUser, Student, InternshipApplication, Faculty, Admin, db, Caretaker, Room, Hostel, RoomChangeRequest
from werkzeug.utils import secure_filename
from flask_mail import Message
from app import mail  
import os
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch

from PyPDF2 import PdfReader, PdfWriter

student_bp = Blueprint("student", __name__)

@student_bp.route("/student", methods=["GET"])
def profile():
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = CustomUser.query.get(user_id)
    student = Student.query.filter_by(student_id=user_id).first()

    if user is None or student is None:
        return redirect(url_for('auth.login'))

    internship_application = InternshipApplication.query.filter_by(email=user.email).first()

    return render_template("student/profile.html", user=user, student=student, internship_application=internship_application)

@student_bp.route("/student/internship_form", methods=["GET"])
def internship_form():
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))

    return render_template("student/internship_form.html")

@student_bp.route("/student/submit_internship_form", methods=["POST"])
def submit_internship_form():
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))

    name = request.form.get('name')
    gender = request.form.get('gender')
    affiliation = request.form.get('affiliation')
    address = request.form.get('address')
    contact_number = request.form.get('contact_number')
    email = request.form.get('email')
    faculty_mentor = request.form.get('faculty_mentor')
    faculty_email = request.form.get('faculty_email')
    arrival_date = request.form.get('arrival_date')
    departure_date = request.form.get('departure_date')
    remarks = request.form.get('remarks')

    id_card = request.files['id_card']
    official_letter = request.files['official_letter']

    if id_card and official_letter:
        # Ensure the uploads directory exists
        uploads_dir = os.path.join(os.getcwd(), 'uploads')
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)

        id_card_filename = secure_filename(id_card.filename)
        official_letter_filename = secure_filename(official_letter.filename)

        id_card.save(os.path.join(uploads_dir, id_card_filename))
        official_letter.save(os.path.join(uploads_dir, official_letter_filename))

        # Convert date strings to Python date objects
        arrival_date = datetime.strptime(arrival_date, '%Y-%m-%d').date()
        departure_date = datetime.strptime(departure_date, '%Y-%m-%d').date()

        internship_application = InternshipApplication(
            name=name,
            gender=gender,
            affiliation=affiliation,
            address=address,
            contact_number=contact_number,
            email=email,
            faculty_mentor=faculty_mentor,
            faculty_email=faculty_email,
            arrival_date=arrival_date,
            departure_date=departure_date,
            id_card=id_card_filename,
            official_letter=official_letter_filename,
            remarks=remarks
        )

        db.session.add(internship_application)
        db.session.commit()

        # Send email to student
        student_msg = Message(
            "Internship Application Submitted",
            sender="johnDoe18262117@gmail.com",
            recipients=[email]
        )
        student_msg.body = f"Dear {name},\n\nYour internship application has been submitted successfully.\n\nThank you!"
        mail.send(student_msg)

        # Send email to faculty
        faculty_msg = Message(
            "New Internship Application for Approval",
            sender="johnDoe18262117@gmail.com",
            recipients=[faculty_email]
        )
        faculty_msg.body = (
            f"Dear {faculty_mentor},\n\n"
            f"A new internship application has been submitted by {name}.\n\n"
            f"Please review and approve the application.\n\n"
            f"Thank you!"
        )
        mail.send(faculty_msg)

        # Send email to HOD
        hod_email = "2022csb1071+hod@iitrpr.ac.in"  # Replace with actual HOD email
        hod_msg = Message(
            "New Internship Application for HOD Approval",
            sender="johnDoe18262117@gmail.com",
            recipients=[hod_email]
        )
        hod_msg.body = (
            f"Dear HOD,\n\n"
            f"A new internship application has been submitted by {name} and approved by {faculty_mentor}.\n\n"
            f"Please review and approve the application.\n\n"
            f"Thank you!"
        )
        mail.send(hod_msg)

        # Send email to admin
        admin_email = "2022csb1071+admin@iitrpr.ac.in"  # Replace with actual admin email
        admin_msg = Message(
            "New Internship Application Submitted",
            sender="johnDoe18262117@gmail.com",
            recipients=[admin_email]
        )
        admin_msg.body = (
            f"Dear Admin,\n\n"
            f"A new internship application has been submitted by {name}.\n\n"
            f"Details:\n"
            f"Name: {name}\n"
            f"Gender: {gender}\n"
            f"Affiliation: {affiliation}\n"
            f"Address: {address}\n"
            f"Contact Number: {contact_number}\n"
            f"Email: {email}\n"
            f"Faculty Mentor: {faculty_mentor}\n"
            f"Faculty Email: {faculty_email}\n"
            f"Arrival Date: {arrival_date}\n"
            f"Departure Date: {departure_date}\n"
            f"Remarks: {remarks}\n\n"
            f"Thank you!"
        )
        mail.send(admin_msg)

        flash("Internship application submitted successfully.", "success")
    else:
        flash("Please upload the required documents.", "danger")

    return redirect(url_for('student.internship_form'))

@student_bp.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(os.path.join(os.getcwd(), 'uploads'), filename)

@student_bp.route("/student/download_application_pdf", methods=["GET"])
def download_application_pdf():
    user_id = session.get('user_id')
    if not user_id or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))

    user = CustomUser.query.get(user_id)
    application = InternshipApplication.query.filter_by(email=user.email, status="Approved by Caretaker").first()

    if not application:
        flash("Application not found or not approved by caretaker.", "danger")
        return redirect(url_for('student.profile'))

    # Path to the PDF template
    template_path = os.path.join("pdf_formats", "summer_interns.pdf")
    if not os.path.exists(template_path):
        flash("Template file not found.", "danger")
        return redirect(url_for('student.profile'))

    # Create a buffer for the overlay
    overlay_buffer = BytesIO()
    c = canvas.Canvas(overlay_buffer, pagesize=letter)

    # Define custom coordinates for each field
    details_coordinates = [
        (215, 615, application.name),
        (215, 592.5, application.gender),
        (215, 570, application.affiliation),
        (215, 535, application.address),
        (330, 500, application.contact_number),
        (450, 500, application.email),
        (217, 639, application.faculty_mentor),
        (350, 639, application.faculty_email),
        (255, 450, application.arrival_date),
        (355, 450, application.departure_date),
        (125, 276, application.remarks if application.remarks else "N/A"),
    ]

    # Draw each field at its specified coordinates
    c.setFont("Helvetica", 10)
    for x, y, value in details_coordinates:
        if value == application.email:  # Check if the current field is the email
            c.setFont("Helvetica", 8)  # Set a smaller font size for the email
            c.drawString(x, y, f"{value}")
            c.setFont("Helvetica", 10)  # Reset to the default font size
        else:
            c.drawString(x, y, f"{value}")

    c.drawString(145, 345, f"{application.arrival_date}")
    c.drawString(155, 311, f"{application.departure_date}")

    # Add Signatures Section (without signature boxes)
    y_position = 200  # Starting y-coordinate for the signatures section
    margin = 50
    signature_width = 100  # Width for each signature

    # Signature labels and positions
    signature_positions = [
        (440,192),
        (60,97),
        (260,100)
    ]

    # Retrieve signature data
    signature_data = [
        Faculty.query.get(application.faculty_signature_id),
        Faculty.query.get(application.hod_signature_id),
        Admin.query.get(application.admin_signature_id)
    ]

    # Draw signatures (with custom width and height for HOD signature)
    for (x, y), signature in zip(signature_positions, signature_data):
        # Place the signature image if it exists
        if signature and signature.signature:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                tmpfile.write(signature.signature)
                tmpfile.flush()

                # Check if the current signature is the HOD's signature
                if signature == Faculty.query.get(application.hod_signature_id):
                    # Custom width and height for HOD signature
                    c.drawImage(tmpfile.name,
                                x, y - 40,  # Adjust y-coordinate to fit the signature
                                width=150,  # Custom width for HOD signature
                                height=55)  # Custom height for HOD signature
                else:
                    # Default width and height for other signatures
                    c.drawImage(tmpfile.name,
                                x, y - 40,
                                width=100,  # Default width
                                height=40)  # Default height

                os.unlink(tmpfile.name)


    c.save()
    overlay_buffer.seek(0)

    # Read the template and overlay
    template_reader = PdfReader(template_path)
    overlay_reader = PdfReader(overlay_buffer)

    # Merge the overlay onto the template (only on the first page)
    writer = PdfWriter()
    for i, page in enumerate(template_reader.pages):
        if i == 0:  # Only overlay data on the first page
            overlay_page = overlay_reader.pages[0]
            page.merge_page(overlay_page)
        writer.add_page(page)

    # Write the final PDF to a buffer
    final_buffer = BytesIO()
    writer.write(final_buffer)
    final_buffer.seek(0)

    return send_file(
        final_buffer,
        as_attachment=True,
        download_name=f'internship_approval_{application.id}.pdf',
        mimetype='application/pdf'
    )

@student_bp.route("/student/complaint", methods=["GET"])
def complaint():
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))

    return render_template("student/complaint.html")

@student_bp.route("/student/submit_complaint", methods=["POST"])
def submit_complaint():
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    student = Student.query.filter_by(student_id=user_id).first()

    if student is None:
        return redirect(url_for('auth.login'))

    complaint_type = request.form.get('complaint_type')
    description = request.form.get('description')

    # Get the caretaker handling the hostel where the student resides
    room = Room.query.filter_by(room_no=student.student_room_no).first()
    if room is None:
        flash("Room not found.", "danger")
        return redirect(url_for('student.complaint'))

    caretaker = Caretaker.query.filter_by(hostel_no=room.hostel_no).first()
    if caretaker is None:
        flash("Caretaker not found.", "danger")
        return redirect(url_for('student.complaint'))

    caretaker_user = CustomUser.query.get(caretaker.user_id)

    # Send email to the caretaker
    msg = Message(
        "New Complaint from Student",
        sender="your-email@example.com",  # Replace with your email
        recipients=[caretaker_user.email]
    )
    msg.body = f"Complaint Type: {complaint_type}\nDescription: {description}\nStudent: {student.user.name}\nRoom No: {student.student_room_no}\nHostel: {room.hostel_no}"
    mail.send(msg)

    flash("Your complaint has been submitted successfully.", "success")
    return redirect(url_for('student.complaint'))

@student_bp.route("/student/room_change", methods=["GET"])
def room_change():
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))

    return render_template("student/room_change.html")

@student_bp.route("/student/submit_room_change", methods=["POST"])
def submit_room_change():
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    student = Student.query.filter_by(student_id=user_id).first()

    if student is None:
        return redirect(url_for('auth.login'))

    reason = request.form.get('reason')
    description = request.form.get('description')

    # Create a new room change request
    room_change_request = RoomChangeRequest(
        student_id=student.student_id,
        reason=reason,
        description=description
    )
    db.session.add(room_change_request)
    db.session.commit()

    # Get the caretaker handling the hostel where the student resides
    room = Room.query.filter_by(room_no=student.student_room_no).first()
    if room is None:
        flash("Room not found.", "danger")
        return redirect(url_for('student.room_change'))

    caretaker = Caretaker.query.filter_by(hostel_no=room.hostel_no).first()
    if caretaker is None:
        flash("Caretaker not found.", "danger")
        return redirect(url_for('student.room_change'))

    caretaker_user = CustomUser.query.get(caretaker.user_id)

    # Send email to the caretaker
    msg = Message(
        "New Room Change Request from Student",
        sender="your-email@example.com",  # Replace with your email
        recipients=[caretaker_user.email]
    )
    msg.body = f"Reason: {reason}\nDescription: {description}\nStudent: {student.user.name}\nRoom No: {student.student_room_no}\nHostel: {room.hostel_no}"
    mail.send(msg)

    flash("Your room change request has been submitted successfully.", "success")
    return redirect(url_for('student.room_change'))