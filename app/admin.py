from flask import Blueprint, render_template, session, redirect, url_for, request, flash, send_file
from app.models import CustomUser, Admin, InternshipApplication, Student, Faculty, db
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