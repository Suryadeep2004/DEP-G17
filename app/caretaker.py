from flask import Blueprint, render_template, session, redirect, url_for, request, flash, send_file
from app.models import Student, CustomUser, Caretaker, InternshipApplication, Room, Hostel, db, RoomChangeRequest, Faculty, Admin, ProjectAccommodationRequest
from flask_mail import Message
from app import mail
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import tempfile
from PyPDF2 import PdfReader, PdfWriter

caretaker_bp = Blueprint("caretaker", __name__)

@caretaker_bp.route("/caretaker", methods=["GET"])
def profile():
    if 'user_id' not in session or session.get('user_role') != 'caretaker':
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = CustomUser.query.get(user_id)
    caretaker = Caretaker.query.filter_by(user_id=user_id).first()

    if user is None or caretaker is None:
        return redirect(url_for('auth.login'))

    hostel = Hostel.query.filter_by(hostel_no=caretaker.hostel_no).first()

    return render_template("caretaker/profile.html", user=user, caretaker=caretaker, hostel=hostel)

@caretaker_bp.route("/caretaker/pending_approvals", methods=["GET", "POST"])
def pending_approvals():
    if 'user_id' not in session or session.get('user_role') != 'caretaker':
        return redirect(url_for('auth.login'))

    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')

    query = InternshipApplication.query.filter_by(status="Approved by Admin")

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

    pending_applications = query.all()

    return render_template("caretaker/pending_approvals.html", pending_applications=pending_applications, search_query=search_query, sort_by=sort_by, sort_order=sort_order)

@caretaker_bp.route("/caretaker/preview_application/<int:application_id>", methods=["GET"])
def preview_application(application_id):
    if 'user_id' not in session or session.get('user_role') != 'caretaker':
        return redirect(url_for('auth.login'))

    application = InternshipApplication.query.get(application_id)
    if not application:
        flash("Application not found.", "danger")
        return redirect(url_for('caretaker.pending_approvals'))

    # Path to the PDF template
    template_path = os.path.join("pdf_formats", "summer_interns.pdf")
    if not os.path.exists(template_path):
        flash("Template file not found.", "danger")
        return redirect(url_for('caretaker.pending_approvals'))

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

    # Return the generated PDF as a response
    return send_file(
        final_buffer,
        as_attachment=False,  # Open in browser instead of downloading
        download_name=f'preview_application_{application.id}.pdf',
        mimetype='application/pdf'
    )

@caretaker_bp.route("/caretaker/approve_application/<int:application_id>", methods=["POST"])
def approve_application(application_id):
    if 'user_id' not in session or session.get('user_role') != 'caretaker':
        return redirect(url_for('auth.login'))

    room_no = request.form.get('room_no')
    application = InternshipApplication.query.get(application_id)

    if application:
        room = Room.query.filter_by(room_no=room_no).first()
        if room:
            application.status = "Approved by Caretaker"
            db.session.commit()

            room.current_occupancy += 1
            db.session.commit()

            student_msg = Message(
                "Internship Application Approved and Room Allocated",
                sender="johnDoe18262117@gmail.com",
                recipients=[application.email]
            )
            student_msg.body = (
                f"Dear {application.name},\n\n"
                f"Your internship application has been approved by the caretaker.\n"
                f"You have been allocated room number {room_no} in hostel {room.hostel_no}.\n\n"
                f"Thank you!"
            )
            mail.send(student_msg)

            flash("Application approved and room allocated.", "success")
        else:
            flash("Room number does not exist.", "danger")
    else:
        flash("Application not found.", "danger")

    return redirect(url_for('caretaker.pending_approvals'))

@caretaker_bp.route("/caretaker/rooms", methods=["GET"])
def rooms():
    if 'user_id' not in session or session.get('user_role') != 'caretaker':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    caretaker = Caretaker.query.filter_by(user_id=user_id).first()

    if caretaker is None:
        return redirect(url_for('auth.login'))

    rooms = Room.query.filter_by(hostel_no=caretaker.hostel_no).all()

    return render_template("caretaker/rooms.html", rooms=rooms)

@caretaker_bp.route("/caretaker/vacant_rooms", methods=["GET"])
def vacant_rooms():
    if 'user_id' not in session or session.get('user_role') != 'caretaker':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    caretaker = Caretaker.query.filter_by(user_id=user_id).first()

    if caretaker is None:
        return redirect(url_for('auth.login'))

    vacant_rooms = Room.query.filter(Room.hostel_no == caretaker.hostel_no, Room.current_occupancy < Room.room_occupancy).all()

    return render_template("caretaker/vacant_rooms.html", vacant_rooms=vacant_rooms)

@caretaker_bp.route("/caretaker/room_change_requests", methods=["GET"])
def room_change_requests():
    if 'user_id' not in session or session.get('user_role') != 'caretaker':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    caretaker = Caretaker.query.filter_by(user_id=user_id).first()

    if caretaker is None:
        return redirect(url_for('auth.login'))

    room_change_requests = RoomChangeRequest.query \
        .join(Student, RoomChangeRequest.student_id == Student.student_id) \
        .join(Room, Room.room_no == Student.student_room_no) \
        .filter(Room.hostel_no == caretaker.hostel_no) \
        .all()

    return render_template("caretaker/room_change_requests.html", room_change_requests=room_change_requests)

@caretaker_bp.route("/caretaker/handle_room_change/<int:request_id>", methods=["POST"])
def handle_room_change(request_id):
    if 'user_id' not in session or session.get('user_role') != 'caretaker':
        return redirect(url_for('auth.login'))

    action = request.form.get('action')
    new_room_no = request.form.get('new_room_no')
    swap_student_email = request.form.get('swap_student_email')

    room_change_request = RoomChangeRequest.query.get(request_id)

    if room_change_request:
        student = Student.query.get(room_change_request.student_id)
        current_room = Room.query.filter_by(room_no=student.student_room_no).first()

        if action == 'approve':
            new_room = Room.query.filter_by(room_no=new_room_no).first()
            if new_room and new_room.current_occupancy < new_room.room_occupancy:
                # Vacate the current room
                current_room.current_occupancy -= 1
                # Allocate the new room
                new_room.current_occupancy += 1
                student.student_room_no = new_room_no
                room_change_request.status = "Approved"
                room_change_request.new_room_no = new_room_no
                db.session.delete(room_change_request)
                db.session.commit()
                flash("Room change approved and new room allocated.", "success")
            else:
                flash("New room is not available.", "danger")
        elif action == 'reject':
            room_change_request.status = "Rejected"
            db.session.delete(room_change_request)
            db.session.commit()
            flash("Room change request rejected.", "danger")
        elif action == 'swap':
            swap_student = Student.query.join(CustomUser).filter(CustomUser.email == swap_student_email).first()
            if swap_student:
                # Swap the room numbers
                student.student_room_no, swap_student.student_room_no = swap_student.student_room_no, student.student_room_no
                room_change_request.status = "Approved"
                room_change_request.new_room_no = swap_student.student_room_no
                db.session.delete(room_change_request)
                db.session.commit()
                flash("Room change approved and rooms swapped.", "success")
            else:
                flash("Swap student not found.", "danger")
    else:
        flash("Room change request not found.", "danger")

    return redirect(url_for('caretaker.room_change_requests'))

@caretaker_bp.route("/caretaker/project_requests", methods=["GET", "POST"])
def project_requests():
    if 'user_id' not in session or session.get('user_role') != 'caretaker':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    caretaker = Caretaker.query.filter_by(user_id=user_id).first()

    if not caretaker:
        flash("Access denied. Only Caretakers can access this page.", "danger")
        return redirect(url_for('auth.login'))

    # Fetch all requests assigned to the caretaker's hostel
    pending_requests = ProjectAccommodationRequest.query.filter_by(
        hostel_allotted=caretaker.hostel_no, status="Pending approval from Caretaker"
    ).all()

    return render_template(
        "caretaker/project_requests.html",
        pending_requests=pending_requests
    )

@caretaker_bp.route("/caretaker/handle_project_request/<int:request_id>", methods=["POST"])
def handle_project_request(request_id):
    if 'user_id' not in session or session.get('user_role') != 'caretaker':
        return redirect(url_for('auth.login'))

    action = request.form.get('action')
    room_no = request.form.get('room_no')
    request_entry = ProjectAccommodationRequest.query.get(request_id)

    if not request_entry:
        flash("Request not found.", "danger")
        return redirect(url_for('caretaker.project_requests'))

    if action == "approve":
        # Check if the room exists and has available capacity
        room = Room.query.filter_by(room_no=room_no, hostel_no=request_entry.hostel_allotted).first()
        if not room:
            flash("Invalid room number or room does not belong to the assigned hostel.", "danger")
            return redirect(url_for('caretaker.project_requests'))

        if room.current_occupancy >= room.room_occupancy:
            flash("Room is already full.", "danger")
            return redirect(url_for('caretaker.project_requests'))

        # Allocate the room to the student
        student = Student.query.filter_by(student_id=request_entry.applicant_id).first()
        if not student:
            flash("Student not found.", "danger")
            return redirect(url_for('caretaker.project_requests'))

        student.student_room_no = room_no
        room.current_occupancy += 1
        request_entry.status = "Approved by Caretaker"

        db.session.commit()
        flash(f"Request approved and room {room_no} allocated to the student.", "success")
    elif action == "reject":
        request_entry.status = "Rejected by Caretaker"
        db.session.commit()
        flash("Request rejected successfully.", "danger")

    return redirect(url_for('caretaker.project_requests'))