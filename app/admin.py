from flask import Blueprint, render_template, session, redirect, url_for, request, flash, send_file
from app.models import CustomUser, Admin, InternshipApplication, Student, Faculty, db, GuestRoomBooking
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
            elif action == 'disapprove':
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
    application = InternshipApplication.query.get(application_id)

    if not application or application.status != "Approved by Caretaker":
        flash("Application not found or not approved by caretaker.", "danger")
        return redirect(url_for('admin.approved_applications'))

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Document margins
    margin = 50
    content_width = width - (2 * margin)
    
    # Background for header
    c.setFillColorRGB(0.95, 0.95, 0.98)  
    c.rect(margin, height - 110, content_width, 60, fill=True, stroke=False)
    
    # Title Styling
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.darkblue)
    c.drawCentredString(width / 2, height - 70, "Internship Application Approval")

    # Underline Title
    c.setStrokeColor(colors.darkblue)
    c.setLineWidth(2)
    c.line(margin, height - 85, width - margin, height - 85)
    
    # Structured layout for application details
    left_x = margin + 20
    right_x = width / 2 + 20
    y_position = height - 140
    field_spacing = 35  

    # Section border
    num_rows = 6  
    details_section_height = (num_rows * field_spacing) + 30  
    c.setStrokeColor(colors.gray)
    c.roundRect(margin, y_position - details_section_height + 5, content_width, details_section_height, 10, stroke=False, fill=False)

    # Application Details
    details = [
        ("Name:", application.name, "Faculty Mentor:", application.faculty_mentor),
        ("Gender:", application.gender, "Faculty Email:", application.faculty_email),
        ("Affiliation:", application.affiliation, "Arrival Date:", application.arrival_date),
        ("Address:", application.address, "Departure Date:", application.departure_date),
        ("Contact Number:", application.contact_number, "Remarks:", application.remarks if application.remarks else "N/A"),
        ("Email:", application.email, "", "")
    ]

    for left_label, left_value, right_label, right_value in details:
        c.setFillColorRGB(0.92, 0.92, 0.95)
        c.rect(left_x - 5, y_position - 5, 120, 25, fill=True, stroke=False)
        
        c.setFillColor(colors.darkblue)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left_x, y_position, left_label)
        
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)  
        c.drawString(left_x + 130, y_position, str(left_value))

        if right_label:
            c.setFillColorRGB(0.92, 0.92, 0.95)
            c.rect(right_x - 5, y_position - 5, 120, 25, fill=True, stroke=False)
            
            c.setFillColor(colors.darkblue)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(right_x, y_position, right_label)
            
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 10)
            
            if right_label == "Faculty Email:":
                c.setFont("Helvetica", 9)
            
            c.drawString(right_x + 130, y_position, str(right_value))

        y_position -= field_spacing

    # Signatures Section
    y_position -= 40
    c.setFillColor(colors.darkblue)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y_position, "Signatures")
    y_position -= 25

    signature_section_height = 110
    c.setStrokeColor(colors.gray)
    c.roundRect(margin, y_position - signature_section_height + 10, content_width, signature_section_height, 10, stroke=True, fill=False)

    # Signature boxes
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

    for (box_x, label), signature in zip(signature_boxes, signature_data):
        c.setStrokeColor(colors.gray)
        c.roundRect(box_x, y_position - 80, signature_width - 20, signature_box_height, 5, stroke=True, fill=False)
        
        if signature and signature.signature:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                tmpfile.write(signature.signature)
                tmpfile.flush()
                c.drawImage(tmpfile.name, 
                           box_x + 10, 
                           y_position - 70, 
                           width=signature_width - 40, 
                           height=50)
                os.unlink(tmpfile.name)
        
        c.setFillColor(colors.darkblue)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(box_x + (signature_width - 20) / 2, y_position - 90, label)

    # Footer
    footer_y = 40
    c.setFillColorRGB(0.95, 0.95, 0.98)
    c.rect(margin, footer_y - 20, content_width, 30, fill=True, stroke=False)
    
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.gray)
    c.drawString(margin + 10, footer_y, "Generated by Hostel Management System")
    c.drawRightString(width - margin - 10, footer_y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, footer_y, f"Application ID: {application.id} | Page 1 of 1")

    c.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f'internship_approval_{application.id}.pdf', mimetype='application/pdf')

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
    elif admin.designation == 'Chief Warden':
        bookings = GuestRoomBooking.query.filter_by(status='Pending approval from Chief Warden').all()

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
            booking.status = 'Rejected'
            flash("Booking rejected.", "danger")
        db.session.commit()
    else:
        flash("Booking not found.", "danger")

    return redirect(url_for('admin.guest_room_booking_approvals'))