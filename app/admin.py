from flask import Blueprint, render_template, session, redirect, url_for, request, flash, send_file
from app.models import CustomUser, Admin, InternshipApplication, Student, Faculty, db, GuestRoomBooking, Warden
import csv
import io
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch
import os
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PyPDF2 import PdfReader, PdfWriter
import tempfile

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin", methods=["GET", "POST"])
def profile():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = CustomUser.query.get(user_id)
    admin = Admin.query.filter_by(admin_id=user_id).first()

    if user is None or admin is None:
        return redirect(url_for('auth.login'))

    if request.method == "POST":
        if 'signature' in request.files:
            signature_file = request.files['signature']
            if signature_file:
                signature_blob = signature_file.read()
                admin.signature = signature_blob
                db.session.commit()
                flash("Signature updated successfully.", "success")
            else:
                flash("No file selected for uploading.", "danger")

    return render_template("admin/profile.html", user=user, admin=admin)

@admin_bp.route("/admin/signature/<int:admin_id>")
def get_signature(admin_id):
    admin = Admin.query.get(admin_id)
    if admin and admin.signature:
        return admin.signature, 200, {'Content-Type': 'image/png'}
    return '', 404

@admin_bp.route("/admin/pending_internship_applications", methods=["GET", "POST"])
def pending_internship_applications():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')

    query = InternshipApplication.query.filter(InternshipApplication.status == "Approved by HOD")

    if search_query:
        query = query.filter(
            InternshipApplication.name.ilike(f'%{search_query}%') |
            InternshipApplication.email.ilike(f'%{search_query}%')
        )

    if sort_by == 'name':
        if sort_order == 'asc':
            query = query.order_by(InternshipApplication.name.asc())
        else:
            query = query.order_by(InternshipApplication.name.desc())
    elif sort_by == 'email':
        if sort_order == 'asc':
            query = query.order_by(InternshipApplication.email.asc())
        else:
            query = query.order_by(InternshipApplication.email.desc())
    elif sort_by == 'status':
        if sort_order == 'asc':
            query = query.order_by(InternshipApplication.status.asc())
        else:
            query = query.order_by(InternshipApplication.status.desc())

    applications = query.all()

    return render_template("admin/pending_internship_applications.html", applications=applications, search_query=search_query, sort_by=sort_by, sort_order=sort_order)

@admin_bp.route("/admin/preview_application/<int:application_id>", methods=["GET"])
def preview_application(application_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    application = InternshipApplication.query.get(application_id)
    if not application:
        flash("Application not found.", "danger")
        return redirect(url_for('admin.pending_internship_applications'))

    # Path to the PDF template
    template_path = os.path.join("pdf_formats", "summer_interns.pdf")
    if not os.path.exists(template_path):
        flash("Template file not found.", "danger")
        return redirect(url_for('admin.pending_internship_applications'))

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

    # Retrieve faculty and HOD signature data
    faculty_signature = Faculty.query.get(application.faculty_signature_id)
    hod_signature = Faculty.query.get(application.hod_signature_id)

    # Draw the faculty signature if it exists
    if faculty_signature and faculty_signature.signature:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
            tmpfile.write(faculty_signature.signature)
            tmpfile.flush()

            # Draw the faculty signature with default width and height
            c.drawImage(tmpfile.name,
                        440, 192 - 40,  # Adjust y-coordinate to fit the signature
                        width=100,  # Default width
                        height=40)  # Default height

        os.unlink(tmpfile.name)  # Delete the temporary file after use

    # Draw the HOD signature if it exists
    if hod_signature and hod_signature.signature:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
            tmpfile.write(hod_signature.signature)
            tmpfile.flush()

            # Draw the HOD signature with custom width and height
            c.drawImage(tmpfile.name,
                        60, 57,  # Adjust coordinates for the HOD signature
                        width=150,  # Custom width for HOD signature
                        height=55)  # Custom height for HOD signature

        os.unlink(tmpfile.name)  # Delete the temporary file after use

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

    # Return the generated PDF as a response
    return send_file(
        final_buffer,
        as_attachment=False,  # Open in browser instead of downloading
        download_name=f'preview_application_{application.id}.pdf',
        mimetype='application/pdf'
    )

@admin_bp.route("/admin/approve_internship_application/<int:application_id>", methods=["POST"])
def approve_internship_application(application_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    admin = Admin.query.filter_by(admin_id=user_id).first()

    action = request.form.get('action')
    application = InternshipApplication.query.get(application_id)

    if application:
        if application.status == "Approved by HOD":
            if action == 'approve':
                application.status = "Approved by Admin"
                application.admin_signature_id = admin.admin_id  # Store admin ID
                flash("Application approved.", "success")
            elif action == 'reject':
                application.status = "Disapproved by Admin"
                flash("Application disapproved.", "danger")
            db.session.commit()
        else:
            flash("Application must be approved by HOD before admin approval.", "warning")
    else:
        flash("Application not found.", "danger")

    return redirect(url_for('admin.pending_internship_applications'))

@admin_bp.route("/admin/approved_applications", methods=["GET"])
def approved_applications():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')

    query = InternshipApplication.query.filter_by(status="Approved by Caretaker")

    if search_query:
        query = query.filter(
            InternshipApplication.name.ilike(f'%{search_query}%') |
            InternshipApplication.email.ilike(f'%{search_query}%')
        )

    if sort_by == 'name':
        if sort_order == 'asc':
            query = query.order_by(InternshipApplication.name.asc())
        else:
            query = query.order_by(InternshipApplication.name.desc())
    elif sort_by == 'email':
        if sort_order == 'asc':
            query = query.order_by(InternshipApplication.email.asc())
        else:
            query = query.order_by(InternshipApplication.email.desc())
    elif sort_by == 'status':
        if sort_order == 'asc':
            query = query.order_by(InternshipApplication.status.asc())
        else:
            query = query.order_by(InternshipApplication.status.desc())

    applications = query.all()

    return render_template("admin/approved_applications.html", applications=applications, search_query=search_query, sort_by=sort_by, sort_order=sort_order)

@admin_bp.route("/admin/add_users", methods=["GET"])
def add_users():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))
    
    return render_template("admin/add_users.html")

@admin_bp.route("/admin/upload_csv", methods=["POST"])
def upload_csv():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    csv_file = request.files['csv_file']
    user_type = request.form.get('user_type')

    if not csv_file or not user_type:
        flash("Please upload a CSV file and select a user type.", "danger")
        return redirect(url_for('admin.add_users'))

    stream = io.StringIO(csv_file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.reader(stream)
    headers = next(csv_input)

    if user_type == "student":
        for row in csv_input:
            student_data = dict(zip(headers, row))
            custom_user = CustomUser(
                email=student_data['email'],
                name=student_data['name'],
                password=student_data['password'],
                is_staff=False,
                is_active=True,
                gender=student_data['gender']
            )
            db.session.add(custom_user)
            db.session.flush()  # Get the ID of the newly added CustomUser

            student = Student(
                student_id=custom_user.id,
                department=student_data['department'],
                student_phone=student_data['student_phone'],
                student_roll=student_data['student_roll'],
                student_year=student_data['student_year'],
                student_room_no=student_data['student_room_no'],
                student_batch=student_data['student_batch']
            )
            db.session.add(student)
        db.session.commit()
        flash("Students added successfully.", "success")

    elif user_type == "faculty":
        for row in csv_input:
            faculty_data = dict(zip(headers, row))
            custom_user = CustomUser(
                email=faculty_data['email'],
                name=faculty_data['name'],
                password=faculty_data['password'],
                is_staff=True,
                is_active=True,
                gender=faculty_data['gender']
            )
            db.session.add(custom_user)
            db.session.flush()  # Get the ID of the newly added CustomUser

            faculty = Faculty(
                faculty_id=custom_user.id,
                department=faculty_data['department'],
                faculty_phone=faculty_data['faculty_phone'],
                is_hod=faculty_data['is_hod'] == 'TRUE',
                signature=faculty_data['signature'].encode() if 'signature' in faculty_data else None
            )
            db.session.add(faculty)
        db.session.commit()
        flash("Faculties added successfully.", "success")

    return redirect(url_for('admin.add_users'))

@admin_bp.route("/admin/download_application_pdf/<int:application_id>", methods=["GET"])
def download_application_pdf(application_id):
    user_id = session.get('user_id')
    if not user_id or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    # Fetch the application using the application_id
    application = InternshipApplication.query.get(application_id)
    if not application:
        flash("Application not found.", "danger")
        return redirect(url_for('admin.pending_internship_applications'))

    # Path to the PDF template
    template_path = os.path.join("pdf_formats", "summer_interns.pdf")
    if not os.path.exists(template_path):
        flash("Template file not found.", "danger")
        return redirect(url_for('admin.pending_internship_applications'))

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
    signature_positions = [
        (440, 192),  # Faculty signature
        (60, 97),    # HOD signature
        (260, 100)   # Admin signature
    ]

    signature_data = [
        Faculty.query.get(application.faculty_signature_id),
        Faculty.query.get(application.hod_signature_id),
        Admin.query.get(application.admin_signature_id)
    ]

    # Draw signatures
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

    # Return the generated PDF as a response
    return send_file(
        final_buffer,
        as_attachment=True,
        download_name=f'internship_approval_{application.id}.pdf',
        mimetype='application/pdf'
    )

@admin_bp.route("/admin/guest_room_booking_approvals", methods=["GET"])
def guest_room_booking_approvals():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    admin = Admin.query.filter_by(admin_id=user_id).first()

    if admin is None or admin.designation not in ['JA (HM)', 'Assistant Registrar (HM)', 'Chief Warden']:
        return redirect(url_for('auth.login'))

    if admin.designation == 'JA (HM)':
        bookings = GuestRoomBooking.query.filter_by(status='Pending approval from JA (HM)').all()
    elif admin.designation == 'Assistant Registrar (HM)':
        bookings = GuestRoomBooking.query.filter_by(status='Pending approval from Assistant Registrar (HM)').all()

    return render_template("admin/guest_room_booking_approvals.html", bookings=bookings, admin=admin)

@admin_bp.route("/admin/handle_guest_room_booking/<int:booking_id>", methods=["POST"])
def handle_guest_room_booking(booking_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    admin = Admin.query.filter_by(admin_id=user_id).first()

    if admin is None or admin.designation not in ['JA (HM)', 'Assistant Registrar (HM)', 'Chief Warden']:
        return redirect(url_for('auth.login'))

    action = request.form.get('action')
    booking = GuestRoomBooking.query.get(booking_id)

    if booking:
        if action == 'approve':
            if admin.designation == 'JA (HM)':
                booking.status = 'Pending approval from Assistant Registrar (HM)'
            elif admin.designation == 'Assistant Registrar (HM)':
                booking.status = 'Pending approval from Chief Warden'
            elif admin.designation == 'Chief Warden':
                # Allocate hostel with available guest rooms
                available_hostels = Hostel.query.filter(Hostel.guest_rooms > 0).all()
                if available_hostels:
                    booking.status = 'Approved'
                    booking.hostel_no = available_hostels[0].hostel_no
                    available_hostels[0].guest_rooms -= 1
                else:
                    flash("No available guest rooms in any hostel.", "danger")
                    return redirect(url_for('admin.guest_room_booking_approvals'))
            flash("Booking approved.", "success")
        elif action == 'reject':
            # Update the status to reflect who rejected the booking
            if admin.designation == 'JA (HM)':
                booking.status = 'Rejected by JA (HM)'
            elif admin.designation == 'Assistant Registrar (HM)':
                booking.status = 'Rejected by Assistant Registrar (HM)'
            elif admin.designation == 'Chief Warden':
                booking.status = 'Rejected by Chief Warden'
            flash("Booking rejected.", "danger")
        db.session.commit()
    else:
        flash("Booking not found.", "danger")

    return redirect(url_for('admin.guest_room_booking_approvals'))

@admin_bp.route("/admin/view_guest_room_booking_pdf/<int:booking_id>", methods=["GET"])
def admin_view_guest_room_booking_pdf(booking_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    booking = GuestRoomBooking.query.get(booking_id)
    if not booking:
        flash("Guest room booking application not found.", "danger")
        return redirect(url_for('admin.guest_room_booking_approvals'))

    # Retrieve the student's details from the Student model
    student = Student.query.filter_by(student_id=booking.applicant_id).first()
    if not student:
        flash("Student details not found.", "danger")
        return redirect(url_for('admin.guest_room_booking_approvals'))

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
        chief_warden_entry = Warden.query.filter_by(is_chief=1).first()
        if chief_warden_entry:
            chief_warden = Faculty.query.filter_by(faculty_id=chief_warden_entry.faculty_id).first()
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

@admin_bp.route("/admin/guest_room_booking_status", methods=["GET"])
def guest_room_booking_status():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    bookings = GuestRoomBooking.query.all()

    return render_template(
        "admin/guest_room_booking_status.html",
        bookings=bookings
    )