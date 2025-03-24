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

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Document margins
    margin = 50
    content_width = width - (2 * margin)
    
    # Background for header - using valid color definition
    c.setFillColorRGB(0.95, 0.95, 0.98)  # Light gray with slight blue tint
    c.rect(margin, height - 110, content_width, 60, fill=True, stroke=False)
    
    # Title Styling
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.darkblue)
    c.drawCentredString(width / 2, height - 70, "Internship Application Approval")

    # Underline Title - thicker and more prominent
    c.setStrokeColor(colors.darkblue)
    c.setLineWidth(2)
    c.line(margin, height - 85, width - margin, height - 85)
    
    # Define structured layout with better spacing
    left_x = margin + 20  # Reduced left margin to give more space
    right_x = width / 2 + 20  # Adjusted right column starting point
    y_position = height - 140
    field_spacing = 35  # Space between fields
    
    # Adjusted spacing to accommodate longer emails
    left_label_width = 120
    right_label_width = 120
    
    # Add section title for personal details
    c.setFillColor(colors.darkblue)
    c.setFont("Helvetica-Bold", 14)
    # c.drawString(margin, y_position, "Application Details")
    y_position -= 25
    
    # Calculate required height for details section based on number of rows
    num_rows = 6  # Number of rows in details
    details_section_height = (num_rows * field_spacing) + 30  # Extra padding
    
    # Draw a border around the details section with rounded corners
    c.setStrokeColor(colors.gray)
    c.setLineWidth(1)
    c.roundRect(margin, y_position - details_section_height + 5, content_width, details_section_height, 10, stroke=False, fill=False)
    
    # Application Details (Left & Right Column)
    details = [
        ("Name:", application.name, "Faculty Mentor:", application.faculty_mentor),
        ("Gender:", application.gender, "Faculty Email:", application.faculty_email),
        ("Affiliation:", application.affiliation, "Arrival Date:", application.arrival_date),
        ("Address:", application.address, "Departure Date:", application.departure_date),
        ("Contact Number:", application.contact_number, "Remarks:", application.remarks if application.remarks else "N/A"),
        ("Email:", application.email, "", "")
    ]

    for left_label, left_value, right_label, right_value in details:
        # Label background for left column
        c.setFillColorRGB(0.92, 0.92, 0.95)
        c.rect(left_x - 5, y_position - 5, left_label_width, 25, fill=True, stroke=False)
        
        # Label and value for left column
        c.setFillColor(colors.darkblue)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left_x, y_position, left_label)
        
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)  # Slightly smaller font for values
        # Position the value with enough space after the label
        c.drawString(left_x + left_label_width + 10, y_position, str(left_value))

        # Only add right column if there's content
        if right_label:
            # Label background for right column
            c.setFillColorRGB(0.92, 0.92, 0.95)
            c.rect(right_x - 5, y_position - 5, right_label_width, 25, fill=True, stroke=False)
            
            # Label and value for right column
            c.setFillColor(colors.darkblue)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(right_x, y_position, right_label)
            
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 10)  # Slightly smaller font for values
            
            # Check if we're handling faculty email to prevent overflow
            if right_label == "Faculty Email:":
                # Use smaller font for email addresses
                c.setFont("Helvetica", 9)
            
            # Position the value with enough space after the label
            c.drawString(right_x + right_label_width + 10, y_position, str(right_value))

        y_position -= field_spacing

    # Recalculate y_position for signature section
    y_position = height - 140 - details_section_height - 20
    
    # Section header for signatures
    c.setFillColor(colors.darkblue)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y_position, "Signatures")
    y_position -= 25
    
    # Draw a border around signature section
    signature_section_height = 110
    c.setStrokeColor(colors.gray)
    c.roundRect(margin, y_position - signature_section_height + 10, content_width, signature_section_height, 10, stroke=True, fill=False)

    # Signature boxes - better aligned
    signature_width = content_width / 3
    signature_box_height = 70
    signature_boxes = [
        (margin + signature_width * 0 + 10, "Faculty Signature"),
        (margin + signature_width * 1 + 10, "HOD Signature"),
        (margin + signature_width * 2 + 10, "Admin Signature")
    ]
    
    signature_data = [
        Faculty.query.get(application.faculty_signature_id),
        Faculty.query.get(application.hod_signature_id),
        Admin.query.get(application.admin_signature_id)
    ]

    # Draw signature boxes and place signatures
    for i, ((box_x, label), signature) in enumerate(zip(signature_boxes, signature_data)):
        # Signature box
        c.setStrokeColor(colors.gray)
        c.roundRect(box_x, y_position - 80, signature_width - 20, signature_box_height, 5, stroke=True, fill=False)
        
        # Place signature image
        if signature and signature.signature:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                tmpfile.write(signature.signature)
                tmpfile.flush()
                # Center signature in box
                c.drawImage(tmpfile.name, 
                           box_x + 10, 
                           y_position - 70, 
                           width=signature_width - 40, 
                           height=50)
                os.unlink(tmpfile.name)
        
        # Signature label
        c.setFillColor(colors.darkblue)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(box_x + (signature_width - 20) / 2, y_position - 90, label)

    # Footer with gradient background
    footer_y = 40
    c.setFillColorRGB(0.95, 0.95, 0.98)
    c.rect(margin, footer_y - 20, content_width, 30, fill=True, stroke=False)
    
    # Footer text
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.gray)
    c.drawString(margin + 10, footer_y, "Generated by Hostel Management System")
    c.drawRightString(width - margin - 10, footer_y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Document ID and page number
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, footer_y, f"Application ID: {application.id} | Page 1 of 1")

    c.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f'internship_approval_{application.id}.pdf', mimetype='application/pdf')

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