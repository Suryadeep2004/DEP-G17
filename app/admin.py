from flask import Blueprint, render_template, session, redirect, url_for, request, flash, send_file
from app.models import CustomUser, Admin, InternshipApplication, Student, Faculty, db, GuestRoomBooking, Warden, ProjectAccommodationRequest, Hostel, Notification, Guest, Remark
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
from sqlalchemy.sql import func
from app.models import Room, Hostel 
from flask import jsonify
from flask_mail import Message
from app import mail

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

@admin_bp.route('/admin/approvals_dashboard', methods=['GET'])
def approvals_dashboard():
    return render_template('admin/approvals_dashboard.html')

@admin_bp.route("/admin/update_profile", methods=["GET", "POST"])
def update_profile():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    user = CustomUser.query.get(user_id)
    admin = Admin.query.filter_by(admin_id=user_id).first()

    if user is None or admin is None:
        return redirect(url_for('auth.login'))

    if request.method == "POST":
        # Get updated data from the form
        name = request.form.get('name')
        phone = request.form.get('phone')

        # Update the database
        user.name = name
        admin.phone = phone

        # Handle signature upload
        if 'signature' in request.files:
            signature_file = request.files['signature']
            if signature_file:
                admin.signature = signature_file.read()

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for('admin.profile'))

    return render_template("admin/update_profile.html", user=user, admin=admin)

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


@admin_bp.route("/admin/guest_room_booking_approvals", methods=["GET", "POST"])
def guest_room_booking_approvals():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    admin = Admin.query.filter_by(admin_id=user_id).first()

    if admin is None or admin.designation not in ['JA (HM)', 'Assistant Registrar (HM)', 'Chief Warden']:
        return redirect(url_for('auth.login'))

    # Fetch bookings based on the admin's designation
    if admin.designation == 'JA (HM)':
        bookings = GuestRoomBooking.query.filter(
            GuestRoomBooking.status.in_([
                'Awaiting Allocation from JA (HM)',
                'Awaiting Payment from Applicant',
                'Awaiting Payment Verification from JA (HM)'
            ])
        )
        # Check for sort parameter
        sort = request.args.get('sort', 'default')
        if sort == 'Awaiting Allocation from JA (HM)':
            bookings = GuestRoomBooking.query.filter(
                GuestRoomBooking.status.in_([
                    'Awaiting Allocation from JA (HM)'
                ])
            ).order_by(GuestRoomBooking.created_at.desc()).all()
        elif sort == 'Awaiting Payment from Applicant':
            bookings = GuestRoomBooking.query.filter(
                GuestRoomBooking.status.in_([
                    'Awaiting Payment from Applicant'
                ])
            ).order_by(GuestRoomBooking.created_at.desc()).all()
        elif sort == 'Awaiting Payment Verification from JA (HM)':
            bookings = GuestRoomBooking.query.filter(
                GuestRoomBooking.status.in_([
                    'Awaiting Payment Verification from JA (HM)'
                ])
            ).order_by(GuestRoomBooking.created_at.desc()).all()
    elif admin.designation == 'Assistant Registrar (HM)':
        bookings = GuestRoomBooking.query.filter(
            GuestRoomBooking.status.in_(['Pending approval from Assistant Registrar (HM)'])
        ).all()
    elif admin.designation == 'Chief Warden':
        bookings = GuestRoomBooking.query.filter_by(status='Pending approval from Chief Warden').all()

    # Handle search and sort functionality
    sort_by = request.args.get('sort_by')
    search_value = request.args.get('search_value')
    # Ensure bookings is a query object
    bookings_query = GuestRoomBooking.query.join(CustomUser, GuestRoomBooking.applicant_id == CustomUser.id)
    if sort_by and search_value:
        if sort_by == 'name':
            bookings_query = bookings_query.filter(CustomUser.name.ilike(f"%{search_value}%"))
        elif sort_by == 'email':
            bookings_query = bookings_query.filter(CustomUser.email.ilike(f"%{search_value}%"))
        elif sort_by == 'arrival_date':
            try:
                search_date = datetime.strptime(search_value, '%Y-%m-%d').date()
                bookings_query = bookings_query.filter(GuestRoomBooking.date_arrival == search_date)
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
        elif sort_by == 'departure_date':
            try:
                search_date = datetime.strptime(search_value, '%Y-%m-%d').date()
                bookings_query = bookings_query.filter(GuestRoomBooking.date_departure == search_date)
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.", "danger")

    bookings = bookings_query.all()

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
    new_remark = Remark.query.filter_by(booking_id=booking_id).order_by(Remark.id.desc()).first()
 
    booking = GuestRoomBooking.query.get(booking_id)
    db.session.add(new_remark)
    # Commit the changes
    db.session.commit()
    flash("Remark added successfully.", "success")

    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for('admin.guest_room_booking_approvals'))

    if action == 'approve':
        if admin.designation == 'JA (HM)' and booking.status == "Awaiting Allocation from JA (HM)": 
            booking.status = "Awaiting Payment from Student"  # Save the remark
            flash("Room Allocated temporarily & Awaiting payment from Student.", "success")
        elif admin.designation == 'JA (HM)' and booking.status == "Awaiting Payment Verification from JA (HM)":
            booking.status = "Pending approval from Assistant Registrar (HM)"# Save the remark
            flash("Payment verified by JA (HM). Forwarded to AR (HM) for approval.", "success")
        elif admin.designation == 'Assistant Registrar (HM)' and booking.status == "Pending approval from Assistant Registrar (HM)":
            booking.status = "Pending approval from Chief Warden" # Save the remark
            flash("Forwarded to Chief Warden for approval.", "success")
        elif admin.designation == 'Chief Warden' and booking.status == "Pending approval from Chief Warden":
            booking.status = "Successful Approval"  # Save the remark
            flash("Booking approved by Chief Warden.", "success")
    elif action == 'reject':
        # Deallocate the room if it was temporarily allocated
        room_no= booking.room_no
        if room_no:
    # Fetch the room and update its is_booked status
            room = Room.query.filter_by(room_no=room_no).first()
            if room:
                room.is_booked = False  # Mark the room as not booked

        booking.room_no = None
        booking.status = f"Rejected by {admin.designation}"  # Save the remark
        flash(f"Booking rejected by {admin.designation}. Temporary room allocation has been deallocated.", "danger")

        # Notify the applicant about the rejection
        applicant_email = None
        student = Student.query.filter_by(student_id=booking.applicant_id).first()
        if student and student.user.email:
            applicant_email = student.user.email
        else:
            guest = Guest.query.filter_by(guest_id=booking.applicant_id).first()
            if guest and guest.user.email:
                applicant_email = guest.user.email

        if applicant_email:
            # Add a notification for the student/guest
            notification = Notification(
                sender_email=admin.user.email,
                recipient_email=applicant_email,
                content=f"Your booking has been cancelled. The temporary room allocation (Room Number: {room_no}) has been revoked by {admin.designation}. Reason for cancellation: {new_remark.content}. If you have any questions, please contact the administration.",
                timestamp=datetime.utcnow()
            )
            db.session.add(notification)

            # Send email notification
            msg = Message(
                "Room Booking Cancelled",
                sender=admin.user.email,
                recipients=[applicant_email]
            )
            msg.body = f"Your booking has been cancelled for Room Number: {room_no} due to: {new_remark.content}."
            mail.send(msg)

    db.session.commit()
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
        guest = Guest.query.filter_by(guest_id=booking.applicant_id).first()
        if not guest:
            flash("Applicant details not found.", "danger")
            return redirect(url_for('admin.guest_room_booking_approvals'))

    template_path = "static/pdf formats/Guest room booking form.pdf"

    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica", 10)

    if student:
        applicant_name = booking.applicant.name
        applicant_phone = student.student_phone or 'N/A'
        applicant_entry = student.student_roll or 'N/A'
        applicant_department_or_address = student.department or 'N/A'
        can.drawString(160, 605, "Student")  # Indicate the role as "Student"
    elif guest:
        applicant_name = booking.applicant.name
        applicant_phone = guest.phone or 'N/A'
        applicant_entry = "N/A"  # Guests don't have a roll number
        applicant_role = "Guest"
        applicant_department_or_address = guest.address or 'N/A'

    # Extract email without domain
    email_without_domain = booking.applicant.email.split('@')[0]

    # Fill data on the PDF
    can.drawString(50, 605, f"{applicant_name}")  # Applicant name
    can.drawString(460, 605, f"{applicant_phone}")  # Applicant phone
    can.drawString(350, 605, f"{applicant_entry}")  # Applicant entry number or N/A
    can.drawString(160, 605, f"{applicant_role}")  # Role: Student or Guest
    can.drawString(265, 605, f"{applicant_department_or_address}")  # Department or Address
    can.drawString(265, 582, f"{email_without_domain}")  #

    # --- Fill Data on PDF ---

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
    if booking.status == "Successful Approval" and booking.hostel:
        can.drawString(300, 128, f"{booking.hostel.hostel_name}")

    # Render signatures based on approval status
    y_position = 150
    signature_section_height = 110
    can.setFont("Helvetica-Bold", 12)

    if booking.status in ["Approved by JA (HM)", "Approved by Assistant Registrar (HM)", "Successful Approval"]:
        ja_hm = Admin.query.filter_by(designation="JA (HM)").first()
        if ja_hm and ja_hm.signature:
            can.drawImage(ImageReader(BytesIO(ja_hm.signature)), 470, y_position - 10, width=50, height=30)

    if booking.status in ["Approved by Assistant Registrar (HM)", "Successful Approval"]:
        ar_hm = Admin.query.filter_by(designation="Assistant Registrar (HM)").first()
        if ar_hm and ar_hm.signature:
            can.drawImage(ImageReader(BytesIO(ar_hm.signature)), 100, y_position - 10 - 70, width=50, height=30)

    if booking.status == "Successful Approval":
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

@admin_bp.route("/admin/guest_room_booking_status", methods=["GET", "POST"])
def guest_room_booking_status():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login')) 

    filter_date = request.form.get('filter_date')  # Get the date from the form

    if filter_date:
        # Convert filter_date to a datetime.date object
        try:
            filter_date_obj = datetime.strptime(filter_date, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
            return redirect(url_for('admin.guest_room_booking_status'))

        # Filter guest room bookings by the selected date
        bookings = GuestRoomBooking.query.filter(
            func.date(GuestRoomBooking.created_at) == filter_date_obj
        ).all()
    else:
        # Fetch all guest room bookings if no date is provided
        bookings = GuestRoomBooking.query.all()

    return render_template(
        "admin/guest_room_booking_status.html",
        bookings=bookings,
        filter_date=filter_date
    )

@admin_bp.route("/admin/ar_pending_project_requests", methods=["GET", "POST"])
def ar_pending_project_requests():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    admin = Admin.query.filter_by(admin_id=user_id).first()

    if not admin or admin.designation != "Assistant Registrar (HM)":
        flash("Access denied. Only Assistant Registrar (HM) can access this page.", "danger")
        return redirect(url_for('auth.login'))

    # Fetch all requests pending approval from Assistant Registrar (HM)
    pending_requests = ProjectAccommodationRequest.query.filter_by(
        status="Pending approval from AR (HM)"
    ).all()

    return render_template(
        "admin/ar_pending_project_requests.html",
        pending_requests=pending_requests
    )

@admin_bp.route("/admin/ar_handle_project_request/<int:request_id>", methods=["POST"])
def ar_handle_project_request(request_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    admin = Admin.query.filter_by(admin_id=user_id).first()

    if not admin or admin.designation != "Assistant Registrar (HM)":
        flash("Access denied. Only Assistant Registrar (HM) can perform this action.", "danger")
        return redirect(url_for('auth.login'))

    action = request.form.get('action')
    request_entry = ProjectAccommodationRequest.query.get(request_id)

    if not request_entry:
        flash("Request not found.", "danger")
        return redirect(url_for('admin.ar_pending_project_requests'))

    if action == "approve":
        request_entry.status = "Pending approval from Chief Warden"
        flash("Request approved and forwarded to Chief Warden.", "success")
    elif action == "reject":
        request_entry.status = "Rejected by Assistant Registrar (HM)"
        flash("Request rejected by Assistant Registrar (HM).", "danger")

    db.session.commit()
    return redirect(url_for('admin.ar_pending_project_requests'))

@admin_bp.route("/admin/view_project_accommodation_pdf/<int:request_id>", methods=["GET"])
def view_project_accommodation_pdf(request_id):
    # Check if the user is logged in and is an admin
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    # Fetch the logged-in admin details
    user_id = session['user_id']
    admin = Admin.query.filter_by(admin_id=user_id).first()

    # Ensure the admin is the Assistant Registrar (HM)
    if not admin or admin.designation != "Assistant Registrar (HM)":
        flash("Access denied. Only Assistant Registrar (HM) can view this PDF.", "danger")
        return redirect(url_for('admin.ar_pending_project_requests'))

    # Fetch the project accommodation request
    request = ProjectAccommodationRequest.query.get(request_id)
    if not request:
        flash("No project accommodation request found.", "danger")
        return redirect(url_for('admin.ar_pending_project_requests'))

    # Path to the PDF template
    template_path = "static/pdf formats/Project Staff booking form.pdf"
    if not os.path.exists(template_path):
        flash("PDF template not found.", "danger")
        return redirect(url_for('admin.ar_pending_project_requests'))

    # Create a buffer for the overlay
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica", 10)

    # Fetch the student's details from the Student model
    student = request.applicant.student
    if not student:
        flash("Student details not found.", "danger")
        return redirect(url_for('admin.ar_pending_project_requests'))

    # Fetch the faculty details
    faculty = Faculty.query.filter_by(faculty_id=request.faculty_id).first()
    if not faculty:
        flash("Faculty details not found.", "danger")
        return redirect(url_for('admin.ar_pending_project_requests'))

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

@admin_bp.route('/admin/add_remark/<int:booking_id>', methods=['POST'])
def add_remark(booking_id):
    remark_content = request.form.get('remark')
    admin = Admin.query.filter_by(admin_id=session['user_id']).first()
    booking = GuestRoomBooking.query.get(booking_id)

    if not booking or not admin:
        flash('Invalid booking or admin.', 'danger')
        return redirect(url_for('admin.guest_room_booking_approvals'))
    
    # Use the name from the related CustomUser model
    admin_name = admin.user.name if admin.user else "Unknown Admin"

    # Save the remark
    new_remark = Remark(
        booking_id=booking_id,
        content=remark_content,
        added_by=admin_name
    )
    db.session.add(new_remark)
    db.session.commit()

    flash('Remark added successfully.', 'success')
    return redirect(url_for('admin.guest_room_booking_approvals'))

@admin_bp.route("/admin/get_room_availability/<int:booking_id>", methods=["GET"])
def get_room_availability(booking_id):
    booking = GuestRoomBooking.query.get(booking_id)
    if not booking:
        print(f"Booking ID {booking_id} not found in the database.")
        return jsonify({"error": "Booking not found"}), 404

    # Fetch all guest rooms associated with hostels
    guest_rooms = Room.query.join(Hostel, Room.hostel_no == Hostel.hostel_no).all()

    # Fetch all bookings up to the current booking ID
    all_bookings = GuestRoomBooking.query.filter(GuestRoomBooking.id <= booking_id).all()

    # Prepare the response with all guest rooms
    rooms = []
    for room in guest_rooms:
        # Check for overlapping bookings manually
        is_booked = False
        for b in all_bookings:
            if (
                b.status in [
                    "Awaiting Allocation from JA (HM)",
                    "Awaiting Payment from Applicant",
                    "Awaiting Payment Verification from JA (HM)",
                    "Pending approval from Assistant Registrar (HM)",
                    "Pending approval from Chief Warden",
                    "Successful Approval"
                ] and
                b.room_no == room.room_no and
                (
                    (b.date_arrival <= booking.date_departure and b.date_departure >= booking.date_arrival) or
                    (b.date_arrival <= booking.date_arrival and b.date_departure >= booking.date_departure)
                ) and
                b.date_departure >= datetime.now().date()
            ):
                is_booked = True
                break

        # Add the room's availability status to the response
        rooms.append({
            "room_id": room.room_no,
            "room_no": room.room_no,
            "is_booked": is_booked
        })

    return jsonify(rooms)


@admin_bp.route("/admin/allocate_room", methods=["POST"])
def allocate_room():
    booking_id = request.form.get("booking_id")
    room_id = request.form.get("room_id")
    remark = request.form.get("remark")

    # Fetch the booking and room
    booking = GuestRoomBooking.query.get(booking_id)
    room = Room.query.get(room_id)

    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for("admin.guest_room_booking_approvals"))

    if not room:
        flash("Room not found.", "danger")
        return redirect(url_for("admin.guest_room_booking_approvals"))

    # Get the logged-in admin
    user_id = session.get("user_id")
    admin = Admin.query.filter_by(admin_id=user_id).first()

    if not admin:
        flash("Admin not found.", "danger")
        return redirect(url_for("auth.login"))

    # Temporarily allocate the room and update the status
    booking.room_no = room.room_no
    booking.status = "Awaiting Payment from Applicant"
    booking.remarks = remark  # Save the remark

    # Notify the applicant (student or guest) to fill payment details
    # Notify the applicant (student or guest) to fill payment details
    applicant_email = None
    student = Student.query.filter_by(student_id=booking.applicant_id).first()
    if student and student.user.email:
        applicant_email = student.user.email
    else:
        guest = Guest.query.filter_by(guest_id=booking.applicant_id).first()
        if guest and guest.user.email:
            applicant_email = guest.user.email

    if applicant_email:
        notification = Notification(
            sender_email=admin.user.email,
            recipient_email=applicant_email,
            content="Your room has been temporarily allocated. Please fill in the payment details.",
            timestamp=datetime.utcnow()
        )
        db.session.add(notification)

        # Send email notification
        msg = Message(
            f"Room Allocation - Payment Details Required {room.room_no}",
            sender=admin.user.email,
            recipients=[applicant_email]
        )
        msg.body = f"Your room has been temporarily allocated. Please log in to your dashboard and fill in the payment details for Room {room.room_no}."
        mail.send(msg)

        # Add a notification for the student
        notification = Notification(
            sender_email=admin.user.email,
            recipient_email=applicant_email,
            content=f"Your room has been temporarily allocated. Room Number: {room.room_no}. Please fill in the payment details.",
            timestamp=datetime.utcnow()
        )
        db.session.add(notification)

    db.session.commit()
    flash(f"Room {room.room_no} temporarily allocated. Status updated to Awaiting Payment from Applicant.", "success")
    return redirect(url_for("admin.guest_room_booking_approvals"))

@admin_bp.route("/admin/send_message", methods=["POST"])
def send_message():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    booking_id = request.form.get('booking_id')
    message_content = request.form.get('message_content')

    # Fetch the booking details
    booking = GuestRoomBooking.query.get(booking_id)
    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for('admin.guest_room_booking_approvals'))

    # Fetch the applicant's email from the appropriate database
    applicant_email = None
    student = Student.query.filter_by(student_id=booking.applicant_id).first()
    if student and student.user.email:
        applicant_email = student.user.email
    else:
        # If not a student, check the Guest database
        guest = Guest.query.filter_by(guest_id=booking.applicant_id).first()
        if guest and guest.user.email:
            applicant_email = guest.user.email

    if not applicant_email:
        flash("Applicant email not found.", "danger")
        return redirect(url_for('admin.guest_room_booking_approvals'))

    # Fetch the sender's email from the logged-in admin's profile
    user_id = session['user_id']
    admin = Admin.query.filter_by(admin_id=user_id).first()
    if not admin or not admin.user.email:
        flash("Unable to fetch sender's email. Please ensure your profile is complete.", "danger")
        return redirect(url_for('admin.guest_room_booking_approvals'))

    sender_email = admin.user.email  # Fetch the email from the admin's profile

    # Save the message in the database
    notification = Notification(
        sender_email=sender_email,
        recipient_email=applicant_email,
        content=message_content,
        timestamp=datetime.utcnow()
    )
    db.session.add(notification)
    db.session.commit()

    # Send the message via email
    msg = Message(
        "Message from JA(HM)",
        sender=sender_email,  # Use the sender's email from the profile
        recipients=[applicant_email]
    )
    msg.body = message_content
    mail.send(msg)

    flash("Message sent successfully and notification saved.", "success")
    return redirect(url_for('admin.guest_room_booking_approvals'))


@admin_bp.route("/admin/notifications", methods=["GET"])
def view_notifications():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    admin = Admin.query.filter_by(admin_id=user_id).first()
    if not admin or not admin.user.email:
        flash("Unable to fetch notifications. Please ensure your profile is complete.", "danger")
        return redirect(url_for('admin.profile'))

    notifications = Notification.query.filter_by(sender_email=admin.user.email).order_by(Notification.timestamp.desc()).all()
    return render_template("admin/notifications.html", notifications=notifications)

@admin_bp.route("/admin/get_payment_details/<int:booking_id>", methods=["GET"])
def get_payment_details(booking_id):
    booking = GuestRoomBooking.query.get(booking_id)
    if not booking or not booking.payment_details:
        return jsonify({"error": "Payment details not found"}), 404
    return jsonify(booking.payment_details)

# filepath: /Users/ashutoshsingh/Documents/DEP-G17/app/admin.py
@admin_bp.route('/admin/get_remarks/<int:booking_id>', methods=['GET'])
def get_remarks(booking_id):
    booking = GuestRoomBooking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    remarks = Remark.query.filter_by(booking_id=booking_id).order_by(Remark.timestamp.desc()).all()
    remarks_data = [
        {
            "added_by": remark.added_by,
            "content": remark.content,
            "timestamp": remark.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
        for remark in remarks
    ]
    return jsonify(remarks_data)

@admin_bp.route('/guest_room_status', methods=['GET', 'POST'])
def guest_room_status():
    filter_date = request.form.get('filter_date')
    if filter_date:
        try:
            filter_date_obj = datetime.strptime(filter_date, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
            return redirect(url_for('admin.guest_room_booking_status'))

        guest_room_bookings = GuestRoomBooking.query.filter(
            func.date(GuestRoomBooking.created_at) == filter_date_obj
        ).all()
    else:
        guest_room_bookings = GuestRoomBooking.query.all()

    return render_template(
        'admin/guest_room_booking_status.html',
        guest_room_bookings=guest_room_bookings,
        filter_date=filter_date
    )