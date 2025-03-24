from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from app.models import Student, CustomUser, Caretaker, InternshipApplication, Room, Hostel, db, RoomChangeRequest
from flask_mail import Message
from app import mail

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