from flask import Blueprint, render_template, session, redirect, url_for, request, flash, send_file, send_from_directory
from app.models import CustomUser, Student, InternshipApplication, Faculty, Admin, db, Caretaker, Room, Hostel, RoomChangeRequest, GuestRoomBooking, Warden, ProjectAccommodationRequest
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

@student_bp.route("/student/guest_room_booking_form", methods=["GET"])
def guest_room_booking_form():
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))

    return render_template("student/guest_room_booking_form.html")

@student_bp.route("/student/submit_guest_room_booking", methods=["POST"])
def submit_guest_room_booking():
    if 'user_id' not in session or session.get('user_role') != 'student':
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
        status='Pending approval from JA (HM)'
    )

    db.session.add(guest_room_booking)
    db.session.commit()

    flash("Guest room booking application submitted successfully.", "success")
    return redirect(url_for('student.profile'))

@student_bp.route("/student/view_guest_room_booking_pdf/<int:booking_id>", methods=["GET"])
def view_guest_room_booking_pdf(booking_id):
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))

    booking = GuestRoomBooking.query.get(booking_id)
    if not booking:
        flash("No guest room booking application found.", "danger")
        return redirect(url_for('student.status'))

    # Retrieve the student's details from the Student model
    student = Student.query.filter_by(student_id=booking.applicant_id).first()
    if not student:
        flash("Student details not found.", "danger")
        return redirect(url_for('student.status'))

    template_path = "static/pdf formats/Guest room booking form.pdf"

    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica", 10)

    # --- Fill Data on PDF ---
    can.drawString(70, 605, f"{booking.applicant.name}")  # Applicant name
    can.drawString(460, 605, f"{student.student_phone or 'N/A'}")  # Use student's phone number
    can.drawString(350, 605, f"{student.student_roll or 'N/A'}")  # Use student's entry number
    can.drawString(160, 605, "Student")  # Indicate the role as "Student"
    can.drawString(265, 605, f"{student.department or 'N/A'}")
    email_without_domain = booking.applicant.email.split('@')[0]
    can.drawString(265, 582, f"{email_without_domain}")

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
    if booking.accommodation_by == "Guest":
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

    # Render hostel details if approved by Chief Warden
    if booking.status == "Approved" and booking.hostel:
        can.drawString(300, 128, f"{booking.hostel.hostel_name}")

    # Render signatures based on approval status
    y_position = 150
    signature_section_height = 110
    can.setFont("Helvetica-Bold", 12)

    if booking.status in ["Approved by JA (HM)", "Approved by Assistant Registrar (HM)", "Approved"]:
        ja_hm = Admin.query.filter_by(designation="JA (HM)").first()
        if ja_hm and ja_hm.signature:
            can.drawImage(ImageReader(BytesIO(ja_hm.signature)), 470, y_position - 10, width=50, height=30)

    if booking.status in ["Approved by Assistant Registrar (HM)", "Approved"]:
        ar_hm = Admin.query.filter_by(designation="Assistant Registrar (HM)").first()
        if ar_hm and ar_hm.signature:
            can.drawImage(ImageReader(BytesIO(ar_hm.signature)), 100, y_position - 10 - 70, width=50, height=30)

    if booking.status == "Approved":
        # Step 1: Retrieve the Chief Warden's entry from the Warden table
        chief_warden_entry = Warden.query.filter_by(is_chief=1).first()

        # Step 2: Use the faculty_id from the Warden table to find the corresponding Faculty entry
        if chief_warden_entry:
            chief_warden = Faculty.query.filter_by(faculty_id=chief_warden_entry.faculty_id).first()

            # Step 3: Check if the Chief Warden exists and has a signature
            if chief_warden and chief_warden.signature:
                can.drawImage(ImageReader(BytesIO(chief_warden.signature)), 470, y_position - 10-70, width=50, height=30)
                
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

@student_bp.route("/student/view_internship_application_pdf/<int:application_id>", methods=["GET"])
def view_internship_application_pdf(application_id):
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))

    application = InternshipApplication.query.get(application_id)
    if not application:
        flash("No internship application found.", "danger")
        return redirect(url_for('student.internship_form_status'))

    # Path to the PDF template
    template_path = "pdf_formats/summer_interns.pdf"

    if not os.path.exists(template_path):
        flash("PDF template not found.", "danger")
        return redirect(url_for('student.internship_form_status'))

    # Create a buffer for the overlay
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica", 10)

    # --- Fill Data on PDF ---
    can.drawString(215, 615, f"{application.name}")  # Applicant name
    can.drawString(215, 592.5, f"{application.gender}")  # Applicant name
    can.drawString(450, 500, f"{application.email}")  # Applicant email
    can.drawString(330, 500, f"{application.contact_number}")  # Contact number
    can.drawString(217, 639, f"{application.faculty_mentor}")  # Faculty mentor
    can.drawString(350, 639, f"{application.faculty_email}")  # Faculty email
    can.drawString(215, 570, f"{application.affiliation}")  # Affiliation
    can.drawString(215, 535, f"{application.address}")  # Address
    can.drawString(255, 450, f"{application.arrival_date.strftime('%d-%m-%Y')}")  # Arrival date
    can.drawString(355, 450, f"{application.departure_date.strftime('%d-%m-%Y')}")  # Departure date
    can.drawString(145, 345, f"{application.arrival_date}")  # Affiliation
    can.drawString(155, 311, f"{application.departure_date}")  # Affiliation
    can.drawString(125, 276, f"{application.remarks or 'N/A'}")  # Remarks

    # Render signatures if available
    if application.status in ["Pending HOD Approval","Rejected by HOD"]:
        faculty = Faculty.query.get(application.faculty_signature_id)
        if faculty and faculty.signature:
            can.drawImage(ImageReader(BytesIO(faculty.signature)), 440, 152, width=100, height=40)

    if application.status in ["Approved by HOD","Disapproved by Admin"]:
        faculty = Faculty.query.get(application.faculty_signature_id)
        hod = Faculty.query.get(application.hod_signature_id)
        if faculty and faculty.signature:
            can.drawImage(ImageReader(BytesIO(faculty.signature)), 440, 152, width=100, height=40)
        if hod and hod.signature:
            can.drawImage(ImageReader(BytesIO(hod.signature)), 60, 57, width=150, height=55)

    if application.status in ["Approved by Admin","Rejected by Caretaker","Approved by Caretaker"]:
        faculty = Faculty.query.get(application.faculty_signature_id)
        hod = Faculty.query.get(application.hod_signature_id)
        admin = Admin.query.get(application.admin_signature_id)
        if faculty and faculty.signature:
            can.drawImage(ImageReader(BytesIO(faculty.signature)), 440, 152, width=100, height=40)
        if hod and hod.signature:
            can.drawImage(ImageReader(BytesIO(hod.signature)), 60, 57, width=150, height=55)
        if admin and admin.signature:
            can.drawImage(ImageReader(BytesIO(admin.signature)), 260, 60, width=100, height=40)

    can.save()
    packet.seek(0)

    # Merge the overlay with the template
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
        download_name="internship_application_filled.pdf",
        as_attachment=False  # This ensures the PDF is displayed inline
    )

@student_bp.route("/student/status", methods=["GET"])
def status():
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    internship_application = InternshipApplication.query.filter_by(id=user_id).first()
    guest_room_bookings = GuestRoomBooking.query.filter_by(applicant_id=user_id).all()

    return render_template(
        "student/status.html",
        internship_application=internship_application,
        guest_room_bookings=guest_room_bookings
    )

@student_bp.route("/student/internship_form_status", methods=["GET"])
def internship_form_status():
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    user = CustomUser.query.get(user_id)

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('auth.login'))

    # Query all internship applications submitted by the student's email
    internship_applications = InternshipApplication.query.filter_by(email=user.email).all()

    if not internship_applications:
        flash("No internship applications found.", "danger")
        return redirect(url_for('student.profile'))

    return render_template(
        "student/internship_form_status.html",
        internship_applications=internship_applications
    )

@student_bp.route("/student/project_accommodation_request_form", methods=["GET"])
def project_accommodation_request_form():
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))

    return render_template("student/project_accommodation_request_form.html")

@student_bp.route("/student/submit_project_accommodation_request", methods=["POST"])
def submit_project_accommodation_request():
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    faculty_email = request.form.get('faculty_email')
    address = request.form.get('address')
    stay_from = request.form.get('stay_from')
    stay_to = request.form.get('stay_to')
    category = request.form.get('category')
    arrival_date = request.form.get('arrival_date')
    arrival_time = request.form.get('arrival_time')
    departure_date = request.form.get('departure_date')
    departure_time = request.form.get('departure_time')
    remarks = request.form.get('remarks')

    # Convert date strings to Python date objects
    stay_from = datetime.strptime(stay_from, '%Y-%m-%d').date()
    stay_to = datetime.strptime(stay_to, '%Y-%m-%d').date()
    arrival_date = datetime.strptime(arrival_date, '%Y-%m-%d').date()
    departure_date = datetime.strptime(departure_date, '%Y-%m-%d').date()

    # Convert time strings to Python time objects
    arrival_time = datetime.strptime(arrival_time, '%H:%M').time()
    departure_time = datetime.strptime(departure_time, '%H:%M').time()

    # Handle file uploads
    offer_letter = request.files['offer_letter']
    id_proof = request.files['id_proof']

    uploads_dir = os.path.join(os.getcwd(), 'uploads')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)

    offer_letter_path = os.path.join(uploads_dir, secure_filename(offer_letter.filename))
    id_proof_path = os.path.join(uploads_dir, secure_filename(id_proof.filename))

    offer_letter.save(offer_letter_path)
    id_proof.save(id_proof_path)

    # Resolve faculty_id from faculty_email using CustomUser
    faculty_user = CustomUser.query.filter_by(email=faculty_email).first()
    if not faculty_user:
        flash("Faculty with the provided email does not exist.", "danger")
        return redirect(url_for('student.project_accommodation_request_form'))

    faculty = Faculty.query.filter_by(faculty_id=faculty_user.id).first()
    if not faculty:
        flash("The provided email does not belong to a faculty member.", "danger")
        return redirect(url_for('student.project_accommodation_request_form'))

    # Create a new ProjectAccommodationRequest entry
    request_entry = ProjectAccommodationRequest(
        applicant_id=user_id,
        faculty_id=faculty.faculty_id,
        address=address,
        stay_from=stay_from,
        stay_to=stay_to,
        category=category,
        arrival_date=arrival_date,
        arrival_time=arrival_time,
        departure_date=departure_date,
        departure_time=departure_time,
        offer_letter_path=offer_letter_path,
        id_proof_path=id_proof_path,
        remarks=remarks,
        status="Pending approval from Faculty"
    )

    db.session.add(request_entry)
    db.session.commit()

    flash("Project Accommodation Request submitted successfully.", "success")
    return redirect(url_for('student.profile'))

@student_bp.route("/student/project_accommodation_status", methods=["GET"])
def project_accommodation_status():
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    # Fetch all project accommodation requests submitted by the student
    project_requests = ProjectAccommodationRequest.query.filter_by(applicant_id=user_id).all()

    if not project_requests:
        flash("No project accommodation requests found.", "info")

    return render_template(
        "student/project_accommodation_status.html",
        project_requests=project_requests
    )

@student_bp.route("/student/view_project_accommodation_pdf/<int:request_id>", methods=["GET"])
def view_project_accommodation_pdf(request_id):
    if 'user_id' not in session or session.get('user_role') != 'student':
        return redirect(url_for('auth.login'))
 
    request = ProjectAccommodationRequest.query.get(request_id)
    if not request:
        flash("No project accommodation request found.", "danger")
        return redirect(url_for('student.project_accommodation_status'))

    # Path to the PDF template
    template_path = "static/pdf formats/Project Staff booking form.pdf"

    if not os.path.exists(template_path):
        flash("PDF template not found.", "danger")
        return redirect(url_for('student.project_accommodation_status'))

    # Create a buffer for the overlay
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica", 10)

    # Fetch the student's details from the Student model
    student = request.applicant.student
    if not student:
        flash("Student details not found.", "danger")
        return redirect(url_for('student.project_accommodation_status'))

    # Fetch the faculty details
    faculty = Faculty.query.filter_by(faculty_id=request.faculty_id).first()
    if not faculty:
        flash("Faculty details not found.", "danger")
        return redirect(url_for('student.project_accommodation_status'))

    # Fetch the hostel name
    hostel_name = request.hostel.hostel_name if request.hostel else "N/A"

    # --- Fill Data on PDF ---
    # Faculty Supervisor Name and Email
    can.drawString(215, 638, f"{faculty.user.name}")  # Faculty supervisor name
    faculty_email_without_domain = faculty.user.email.split('@')[0]  # Remove the domain part
    can.drawString(375, 638, f"{faculty_email_without_domain}")  # Faculty email without domain

    # Applicant Details
    can.drawString(215, 615, f"{request.applicant.name}")  # Applicant name
    can.drawString(215, 592, f"{request.applicant.gender}")  # Applicant gender (from CustomUser model)
    can.drawString(215, 569, f"{student.department}")  # Applicant department
    can.drawString(215, 535, f"{request.address}")  # Full address of student applicant
    can.drawString(265, 500, f"{student.student_phone}")  # Student contact
    can.drawString(439, 500, f"{request.applicant.email}")  # Student email

    # Faculty Contact
    can.drawString(215, 477, f"{faculty.faculty_phone or 'N/A'}")  # Faculty contact

    # Category of Hostel
    if request.category == "A":
        can.drawString(327, 282, "\u2713")  # Tick for Category A
    elif request.category == "B":
        can.drawString(390, 282, "\u2713")  # Tick for Category B

    # Date and Time of Arrival and Departure
    # Extract arrival date components
    arrival_day = request.arrival_date.strftime('%d')
    arrival_month = request.arrival_date.strftime('%m')
    arrival_year = request.arrival_date.strftime('%Y')
    arrival_time = request.arrival_time.strftime('%H:%M')  # 24-hour format

    # Extract departure date components
    departure_day = request.departure_date.strftime('%d')
    departure_month = request.departure_date.strftime('%m')
    departure_year = request.departure_date.strftime('%Y')
    departure_time = request.departure_time.strftime('%H:%M')  # 24-hour format

    # Render arrival date components
    can.drawString(242, 449, f"{arrival_day}")  # Arrival day
    can.drawString(270, 449, f"{arrival_month}")  # Arrival month
    can.drawString(315, 449, f"{(int(arrival_year))%100}")  # Arrival year
    can.drawString(242-100, 248, f"{arrival_day}")  # Arrival day
    can.drawString(270-100+10, 248, f"{arrival_month}")  # Arrival month
    can.drawString(315-100+15, 248, f"{(int(arrival_year))%100}")  # Arrival year
    can.drawString(360, 248, f"{arrival_time}")  # Arrival time

    # Render departure date components
    can.drawString(350, 449, f"{departure_day}")  # Departure day
    can.drawString(378, 449, f"{departure_month}")  # Departure month
    can.drawString(423, 449, f"{(int(departure_year))%100}")  # Departure year
    can.drawString(142+10, 224, f"{departure_day}")  # Departure day
    can.drawString(270-100+20, 224, f"{departure_month}")  # Departure month
    can.drawString(315-100+25, 224, f"{(int(departure_year))%100}")  # Departure year
    can.drawString(360, 224, f"{departure_time}")  # Departure time
    

    # Remarks
    can.drawString(128, 201, f"{request.remarks or 'N/A'}")  # Remarks

    # Hostel Name
    can.drawString(130, 51, f"{hostel_name}")  # Hostel name

    # Signatures
    if request.status == "Approved by Caretaker":
        # Mentor Faculty Signature
        mentor_signature = faculty.signature
        if mentor_signature:
            can.drawImage(ImageReader(BytesIO(mentor_signature)), 460, 145, width=50, height=30)  # Mentor Faculty Signature

        # Fetch HOD signature
        hod = Faculty.query.filter_by(is_hod=True).first()
        if hod and hod.signature:
            can.drawImage(ImageReader(BytesIO(hod.signature)), 100, 99, width=50, height=30)  # HOD Signature

        # Fetch AR (HM) signature
        ar_hm = Admin.query.filter_by(designation="Assistant Registrar (HM)").first()
        if ar_hm and ar_hm.signature:
            can.drawImage(ImageReader(BytesIO(ar_hm.signature)), 270, 100, width=50, height=30)  # AR (HM) Signature

        # Fetch Chief Warden signature
        chief_warden_entry = Warden.query.filter_by(is_chief=True).first()
        if chief_warden_entry:
            chief_warden = Faculty.query.filter_by(faculty_id=chief_warden_entry.faculty_id).first()
            if chief_warden and chief_warden.signature:
                can.drawImage(ImageReader(BytesIO(chief_warden.signature)), 465, 100, width=50, height=30)  # Chief Warden Signature

    can.save()
    packet.seek(0)

    # Merge the overlay with the template
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
        download_name="project_accommodation_request.pdf",
        as_attachment=False  # This ensures the PDF is displayed inline
    )