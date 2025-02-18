from flask import Blueprint, render_template, session, redirect, url_for
from app.models import CustomUser, Caretaker, Hostel

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
    hostel_name = hostel.hostel_name if hostel else 'Undefined'

    return render_template("caretaker/profile.html", user=user, caretaker=caretaker, hostel_name=hostel_name)