from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from app.models import CustomUser, Admin, InternshipApplication, db

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin", methods=["GET"])
def profile():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = CustomUser.query.get(user_id)
    admin = Admin.query.filter_by(admin_id=user_id).first()

    if user is None or admin is None:
        return redirect(url_for('auth.login'))

    return render_template("admin/profile.html", user=user, admin=admin)

@admin_bp.route("/admin/pending_internship_applications", methods=["GET"])
def pending_internship_applications():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    applications = InternshipApplication.query.filter(InternshipApplication.status != "Approved by Admin").all()

    return render_template("admin/pending_internship_applications.html", applications=applications)

@admin_bp.route("/admin/approve_internship_application/<int:application_id>", methods=["POST"])
def approve_internship_application(application_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('auth.login'))

    action = request.form.get('action')
    application = InternshipApplication.query.get(application_id)

    if application:
        if application.status == "Approved by HOD":
            if action == 'approve':
                application.status = "Approved by Admin"
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