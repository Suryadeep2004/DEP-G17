from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify, send_file
from app.models import Warden, DummyBatch, DummyHostel, DummyAllocation, CustomUser, Faculty, InternshipApplication, GuestRoomBooking, Hostel, Student
from app.database import db
from flask_mail import Message
from app import mail 
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

faculty_bp = Blueprint("faculty", __name__)

@faculty_bp.route("/faculty", methods=["GET", "POST"])
def profile():
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = CustomUser.query.get(user_id)
    faculty = Faculty.query.filter_by(faculty_id=user_id).first()

    if user is None or faculty is None:
        return redirect(url_for('auth.login'))

    if request.method == "POST":
        if 'signature' in request.files:
            signature_file = request.files['signature']
            if signature_file:
                signature_blob = signature_file.read()
                faculty.signature = signature_blob
                db.session.commit()
                flash("Signature updated successfully.", "success")
            else:
                flash("No file selected for uploading.", "danger")

    return render_template("faculty/profile.html", user=user, faculty=faculty)

@faculty_bp.route("/faculty/signature/<int:faculty_id>")
def get_signature(faculty_id):
    faculty = Faculty.query.get(faculty_id)
    if faculty and faculty.signature:
        return faculty.signature, 200, {'Content-Type': 'image/png'}
    return '', 404

@faculty_bp.route("/faculty/pending_approvals", methods=["GET", "POST"])
def pending_approvals():
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    user = CustomUser.query.get(user_id)
    faculty = Faculty.query.filter_by(faculty_id=user_id).first()

    if faculty is None:
        return redirect(url_for('auth.login'))

    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')

    query = InternshipApplication.query.filter_by(faculty_email=user.email, status="Pending Faculty Approval")

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

    return render_template("faculty/pending_approval.html", pending_applications=pending_applications, search_query=search_query, sort_by=sort_by, sort_order=sort_order)

@faculty_bp.route("/faculty/approve_application/<int:application_id>", methods=["POST"])
def approve_application(application_id):
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    faculty = Faculty.query.filter_by(faculty_id=user_id).first()

    action = request.form.get('action')
    application = InternshipApplication.query.get(application_id)

    if application:
        if action == 'approve':
            application.status = "Pending HOD Approval"
            application.faculty_signature_id = faculty.faculty_id
            db.session.commit()

            hod = Faculty.query.filter_by(is_hod=True).first()
            hod_email = hod.user.email
            hod_msg = Message(
                "New Internship Application for HOD Approval",
                sender="johnDoe18262117@gmail.com",
                recipients=[hod_email]
            )
            hod_msg.body = (
                f"Dear HOD,\n\n"
                f"A new internship application has been submitted by {application.name} and approved by {application.faculty_mentor}.\n\n"
                f"Please review and approve the application.\n\n"
                f"Thank you!"
            )
            mail.send(hod_msg)

            flash("Application approved and forwarded to HOD for approval.", "success")
        elif action == 'reject':
            application.status = "Rejected by Faculty"
            db.session.commit()
            flash("Application rejected.", "danger")
    else:
        flash("Application not found.", "danger")

    return redirect(url_for('faculty.pending_approvals'))

@faculty_bp.route("/faculty/hod_pending_approvals", methods=["GET", "POST"])
def hod_pending_approvals():
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    faculty = Faculty.query.filter_by(faculty_id=user_id).first()

    if faculty is None or not faculty.is_hod:
        return redirect(url_for('auth.login'))

    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')

    query = InternshipApplication.query.filter_by(status="Pending HOD Approval")

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

    return render_template("faculty/hod_pending_approval.html", pending_applications=pending_applications, search_query=search_query, sort_by=sort_by, sort_order=sort_order)

@faculty_bp.route("/faculty/hod_approve_application/<int:application_id>", methods=["POST"])
def hod_approve_application(application_id):
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    faculty = Faculty.query.filter_by(faculty_id=user_id).first()

    if faculty is None or not faculty.is_hod:
        return redirect(url_for('auth.login'))

    action = request.form.get('action')
    application = InternshipApplication.query.get(application_id)

    if application:
        if action == 'approve':
            application.status = "Approved by HOD"
            application.hod_signature_id = faculty.faculty_id  
            db.session.commit()

            # Send email to student
            student_msg = Message(
                "Internship Application Approved by HOD",
                sender="johnDoe18262117@gmail.com",
                recipients=[application.email]
            )
            student_msg.body = f"Dear {application.name},\n\nYour internship application has been approved by the HOD.\n\nThank you!"
            mail.send(student_msg)

            flash("Application approved by HOD.", "success")
        elif action == 'reject':
            application.status = "Rejected by HOD"
            db.session.commit()

            # Send email to student
            student_msg = Message(
                "Internship Application Rejected by HOD",
                sender="johnDoe18262117@gmail.com",
                recipients=[application.email]
            )
            student_msg.body = f"Dear {application.name},\n\nYour internship application has been rejected by the HOD.\n\nThank you!"
            mail.send(student_msg)

            flash("Application rejected by HOD.", "danger")
    else:
        flash("Application not found.", "danger")

    return redirect(url_for('faculty.hod_pending_approvals'))

@faculty_bp.route("/faculty/batch_allocation", methods=["GET"])
def batch_allocation():
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    faculty = Faculty.query.filter_by(faculty_id=user_id).first()
    warden = Warden.query.filter_by(faculty_id=user_id).first()

    if faculty is None or warden is None or not warden.is_chief:
        return redirect(url_for('auth.login'))

    batches = DummyBatch.query.all()
    hostels = DummyHostel.query.all()

    allocation_data = {}
    for batch in batches:
        allocation_data[batch.batch_no] = {}
        for hostel in hostels:
            allocation = DummyAllocation.query.filter_by(batch_id=batch.id, hostel_id=hostel.id).first()
            allocation_data[batch.batch_no][hostel.hostel_no] = allocation.number_of_students if allocation else 0

    return render_template("faculty/batch_allocation.html", batches=batches, hostels=hostels, allocation_data=allocation_data)

@faculty_bp.route("/faculty/allocate_batch_sandbox", methods=["GET"])
def allocate_batch_sandbox():
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    faculty = Faculty.query.filter_by(faculty_id=user_id).first()
    warden = Warden.query.filter_by(faculty_id=user_id).first()

    if faculty is None or warden is None or not warden.is_chief:
        return redirect(url_for('auth.login'))

    batches = DummyBatch.query.all()
    hostels = DummyHostel.query.all()

    # Calculate unallocated students for each batch
    for batch in batches:
        allocated_students = db.session.query(db.func.sum(DummyAllocation.number_of_students)).filter_by(batch_id=batch.id).scalar() or 0
        batch.unallocated_students = batch.number_of_students - allocated_students

    # Calculate vacant capacity for each hostel
    for hostel in hostels:
        allocated_students = db.session.query(db.func.sum(DummyAllocation.number_of_students)).filter_by(hostel_id=hostel.id).scalar() or 0
        hostel.vacant_capacity = hostel.capacity - allocated_students

    return render_template("faculty/allocate_batch_sandbox.html", batches=batches, hostels=hostels)
    
@faculty_bp.route("/faculty/save_batch_allocation", methods=["POST"])
def save_batch_allocation():
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))

    data = request.json
    allocations = data.get("allocations", [])

    for alloc in allocations:
        batch_id = alloc["batchId"]
        hostel_id = alloc["hostelId"]
        num_students = alloc["numStudents"]

        batch = DummyBatch.query.get(batch_id)
        hostel = DummyHostel.query.get(hostel_id)

        if not batch or not hostel:
            return jsonify({"error": "Invalid batch or hostel"}), 400

        # Constraint: Ensure enough vacancies in hostel
        total_allocated = db.session.query(db.func.sum(DummyAllocation.number_of_students)) \
            .filter_by(hostel_id=hostel_id).scalar() or 0

        if total_allocated + num_students > hostel.capacity:
            return jsonify({"error": "Not enough vacancies"}), 400

        # Constraint: Ensure batch has enough unallocated students
        existing_alloc = db.session.query(db.func.sum(DummyAllocation.number_of_students)) \
            .filter_by(batch_id=batch_id).scalar() or 0

        if existing_alloc + num_students > batch.number_of_students:
            return jsonify({"error": "Not enough students left in batch"}), 400

        # Save Allocation
        allocation = DummyAllocation(batch_id=batch_id, hostel_id=hostel_id, number_of_students=num_students)
        db.session.add(allocation)

    db.session.commit()
    return jsonify({"message": "Batch allocations saved successfully!"})

@faculty_bp.route("/faculty/guest_room_booking_approvals", methods=["GET"])
def guest_room_booking_approvals():
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    faculty = Faculty.query.filter_by(faculty_id=user_id).first()
    warden = Warden.query.filter_by(faculty_id=user_id).first()

    if faculty is None or warden is None or not warden.is_chief:
        return redirect(url_for('auth.login'))

    bookings = GuestRoomBooking.query.filter_by(status='Pending approval from Chief Warden').all()
    available_hostels = Hostel.query.filter(Hostel.guest_rooms > 0).all()

    return render_template("faculty/guest_room_booking_approvals.html", bookings=bookings, faculty=faculty, hostels=available_hostels)

@faculty_bp.route("/faculty/handle_guest_room_booking/<int:booking_id>", methods=["POST"])
def handle_guest_room_booking(booking_id):
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    faculty = Faculty.query.filter_by(faculty_id=user_id).first()
    warden = Warden.query.filter_by(faculty_id=user_id).first()

    if faculty is None or warden is None or not warden.is_chief:
        return redirect(url_for('auth.login'))

    action = request.form.get('action')
    booking = GuestRoomBooking.query.get(booking_id)

    if booking:
        if action == 'approve':
            if booking.status == 'Pending approval from Chief Warden':
                hostel_no = request.form.get('hostel_no')
                hostel = Hostel.query.filter_by(hostel_no=hostel_no).first()
                if hostel and hostel.guest_rooms > 0:
                    booking.status = 'Approved'
                    booking.hostel_no = hostel_no
                    hostel.guest_rooms -= 1
                    db.session.commit()
                    flash("Booking approved and hostel allocated.", "success")
                else:
                    flash("Selected hostel does not have available guest rooms.", "danger")
            else:
                flash("Booking is not pending approval from Chief Warden.", "warning")
        elif action == 'reject':
            booking.status = 'Rejected by Chief Warden'
            db.session.commit()
            flash("Booking rejected.", "danger")
    else:
        flash("Booking not found.", "danger")

    return redirect(url_for('faculty.guest_room_booking_approvals'))

@faculty_bp.route("/faculty/view_guest_room_booking_pdf/<int:booking_id>", methods=["GET"])
def faculty_view_guest_room_booking_pdf(booking_id):
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))

    booking = GuestRoomBooking.query.get(booking_id)
    if not booking:
        flash("Guest room booking application not found.", "danger")
        return redirect(url_for('faculty.guest_room_booking_approvals'))

    # Retrieve the student's details from the Student model
    student = Student.query.filter_by(student_id=booking.applicant_id).first()
    if not student:
        flash("Student details not found.", "danger")
        return redirect(url_for('faculty.guest_room_booking_approvals'))

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

    output = BytesIO()
    writer.write(output)
    output.seek(0)

    return send_file(
        output,
        mimetype="application/pdf",
        download_name="guest_room_booking_filled.pdf",
        as_attachment=False  # This ensures the PDF is displayed inline
    )