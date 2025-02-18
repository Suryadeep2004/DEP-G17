from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from app.models import CustomUser, Faculty, Application, db

faculty_bp = Blueprint("faculty", __name__)

@faculty_bp.route("/faculty", methods=["GET"])
def profile():
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = CustomUser.query.get(user_id)
    faculty = Faculty.query.filter_by(faculty_id=user_id).first()

    if user is None or faculty is None:
        return redirect(url_for('auth.login'))

    return render_template("faculty/profile.html", user=user, faculty=faculty)

@faculty_bp.route("/faculty/pending_approvals", methods=["GET"])
def pending_approvals():
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    faculty = Faculty.query.filter_by(faculty_id=user_id).first()

    if faculty is None:
        return redirect(url_for('auth.login'))

    pending_applications = Application.query.filter_by(faculty_id=user_id, status="Pending").all()

    return render_template("faculty/pending_approval.html", pending_applications=pending_applications)

@faculty_bp.route("/faculty/approve_application/<int:application_id>", methods=["POST"])
def approve_application(application_id):
    if 'user_id' not in session or session.get('user_role') != 'faculty':
        return redirect(url_for('auth.login'))

    action = request.form.get('action')
    application = Application.query.get(application_id)

    if application:
        if action == 'approve':
            application.status = "Approved by Faculty"
            flash("Application approved and forwarded to HOD for approval.", "success")
        elif action == 'reject':
            application.status = "Rejected by Faculty"
            flash("Application rejected.", "danger")
        db.session.commit()
    else:
        flash("Application not found.", "danger")

    return redirect(url_for('faculty.pending_approvals'))