from app.database import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON  # Use this for PostgreSQL
class CustomUser(db.Model):
    __tablename__ = 'custom_user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_staff = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    gender = db.Column(db.String(20), default='Not Specified')

    student = db.relationship('Student', backref='user', uselist=False, cascade="all, delete")
    caretaker = db.relationship('Caretaker', backref='user', uselist=False, cascade="all, delete")
    faculty = db.relationship('Faculty', backref='user', uselist=False, cascade="all, delete")
    admin = db.relationship('Admin', backref='user', uselist=False, cascade="all, delete")
    guest = db.relationship('Guest', backref='user', uselist=False, cascade="all, delete")

    def set_password(self, password):
        self.password = password

    def check_password(self, password):
        return self.password == password

class Student(db.Model):
    __tablename__ = 'student'
    student_id = db.Column(db.Integer, db.ForeignKey('custom_user.id', ondelete='CASCADE'), primary_key=True)
    department = db.Column(db.String(100))
    student_phone = db.Column(db.String(10))
    student_roll = db.Column(db.String(15), unique=True)
    student_year = db.Column(db.Integer)
    student_room_no = db.Column(db.String(20))
    student_batch = db.Column(db.String(20))

class Faculty(db.Model):
    __tablename__ = 'faculty'
    faculty_id = db.Column(db.Integer, db.ForeignKey('custom_user.id', ondelete='CASCADE'), primary_key=True)
    department = db.Column(db.String(100), nullable=False)
    faculty_phone = db.Column(db.String(10), unique=True, nullable=False)
    is_hod = db.Column(db.Boolean, default=False)
    signature = db.Column(db.LargeBinary)

    warden = db.relationship('Warden', backref='faculty', uselist=False, cascade="all, delete")

class Caretaker(db.Model):
    __tablename__ = 'caretaker'
    caretaker_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('custom_user.id', ondelete='CASCADE'), unique=True, nullable=False)
    hostel_no = db.Column(db.String(20), db.ForeignKey('hostel.hostel_no', ondelete='CASCADE'), nullable=False)
    phone = db.Column(db.String(15))  # Add this field for phone number
    signature = db.Column(db.LargeBinary)  # Add this field for signature
 
class CaretakerHistory(db.Model):
    __tablename__ = 'caretaker_history'
    id = db.Column(db.Integer, primary_key=True)
    caretaker_id = db.Column(db.Integer, db.ForeignKey('custom_user.id', ondelete='SET NULL'))
    hostel_no = db.Column(db.String(20), db.ForeignKey('hostel.hostel_no', ondelete='CASCADE'))
    start_date = db.Column(db.DateTime, default=db.func.current_timestamp())  
    end_date = db.Column(db.DateTime)  

class Admin(db.Model):
    __tablename__ = 'admin'
    admin_id = db.Column(db.Integer, db.ForeignKey('custom_user.id', ondelete='CASCADE'), primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    signature = db.Column(db.LargeBinary)
    designation = db.Column(db.String(100)) 

class Hostel(db.Model):
    __tablename__ = 'hostel'
    hostel_no = db.Column(db.String(20), primary_key=True)
    hostel_name = db.Column(db.String(100))
    hostel_type = db.Column(db.String(50))
    num_floors = db.Column(db.Integer)
    capacity = db.Column(db.Integer)
    guest_rooms = db.Column(db.Integer, default=4)  # New attribute

    caretakers = db.relationship('Caretaker', backref='hostel', cascade="all, delete")
    wardens = db.relationship('Warden', backref='hostel', cascade="all, delete")
    rooms = db.relationship('Room', backref='hostel', cascade="all, delete")

class Room(db.Model):
    __tablename__ = 'room'
    room_no = db.Column(db.String(20), primary_key=True)
    floor = db.Column(db.Integer)
    hostel_no = db.Column(db.String(20), db.ForeignKey('hostel.hostel_no', ondelete='CASCADE'))
    room_occupancy = db.Column(db.Integer)
    current_occupancy = db.Column(db.Integer, default=0)

class Warden(db.Model):
    __tablename__ = 'warden'
    warden_id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.faculty_id', ondelete='CASCADE'), unique=True, nullable=False)
    hostel_no = db.Column(db.String(20), db.ForeignKey('hostel.hostel_no', ondelete='CASCADE'), nullable=False)
    is_chief = db.Column(db.Boolean, default=False)

class Batch(db.Model):
    __tablename__ = 'batch'
    batch_no = db.Column(db.String(20), primary_key=True)
    number_of_students = db.Column(db.Integer)
    number_of_girls = db.Column(db.Integer)
    number_of_boys = db.Column(db.Integer)

class InternshipApplication(db.Model):
    __tablename__ = 'internship_application'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    affiliation = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    contact_number = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    faculty_mentor = db.Column(db.String(100), nullable=False)
    faculty_email = db.Column(db.String(100), nullable=False)
    arrival_date = db.Column(db.Date, nullable=False)
    departure_date = db.Column(db.Date, nullable=False)
    id_card = db.Column(db.String(100), nullable=False)
    official_letter = db.Column(db.String(100), nullable=False)
    remarks = db.Column(db.String(300))
    status = db.Column(db.String(50), default="Pending Faculty Approval", nullable=False)
    faculty_signature_id = db.Column(db.Integer, db.ForeignKey('faculty.faculty_id'))  
    hod_signature_id = db.Column(db.Integer, db.ForeignKey('faculty.faculty_id'))  
    admin_signature_id = db.Column(db.Integer, db.ForeignKey('admin.admin_id'))  
    approval_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DummyBatch(db.Model):
    __tablename__ = 'dummy_batch'
    id = db.Column(db.Integer, primary_key=True)
    batch_no = db.Column(db.String(20), unique=True, nullable=False)
    number_of_students = db.Column(db.Integer, nullable=False)
    number_of_boys = db.Column(db.Integer, nullable=False)
    number_of_girls = db.Column(db.Integer, nullable=False)

class DummyHostel(db.Model):
    __tablename__ = 'dummy_hostel'
    id = db.Column(db.Integer, primary_key=True)
    hostel_no = db.Column(db.String(20), unique=True, nullable=False)
    hostel_name = db.Column(db.String(100), nullable=False)
    hostel_type = db.Column(db.String(50), nullable=False)  # 'Boys' or 'Girls'
    capacity = db.Column(db.Integer, nullable=False)

class DummyAllocation(db.Model):
    __tablename__ = 'dummy_allocation'
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('dummy_batch.id'), nullable=False)
    hostel_id = db.Column(db.Integer, db.ForeignKey('dummy_hostel.id'), nullable=False)
    number_of_students = db.Column(db.Integer, nullable=False)

    batch = db.relationship('DummyBatch', backref=db.backref('allocations', cascade='all, delete-orphan'))
    hostel = db.relationship('DummyHostel', backref=db.backref('allocations', cascade='all, delete-orphan'))

class RoomChangeRequest(db.Model):
    __tablename__ = 'room_change_request'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id', ondelete='CASCADE'), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="Pending", nullable=False)
    new_room_no = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    student = db.relationship('Student', backref=db.backref('room_change_requests', cascade='all, delete-orphan'))

# class GuestRoomBooking(db.Model):
#     __tablename__ = 'guest_room_booking'
#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     applicant_id = db.Column(db.Integer, db.ForeignKey('custom_user.id', ondelete='CASCADE'), nullable=False)
#     room_no = db.Column(db.String(20), db.ForeignKey('room.room_no', ondelete='SET NULL'))  # Add this field
#     total_guests = db.Column(db.Integer, nullable=False)
#     guests_male = db.Column(db.Integer, nullable=False)
#     guests_female = db.Column(db.Integer, nullable=False)
#     guest_names = db.Column(db.Text, nullable=False)
#     relation_with_applicant = db.Column(db.Text, nullable=False)
#     guest_address = db.Column(db.Text, nullable=False)
#     guest_contact = db.Column(db.Text, nullable=False)
#     guest_email = db.Column(db.Text)
#     purpose_of_visit = db.Column(db.Text, nullable=False)
#     room_category = db.Column(db.Text, nullable=False)
#     date_arrival = db.Column(db.Date, nullable=False)
#     time_arrival = db.Column(db.Time, nullable=False)
#     date_departure = db.Column(db.Date, nullable=False)
#     time_departure = db.Column(db.Time, nullable=False)
#     accommodation_by = db.Column(db.Text, nullable=False)
#     remarks = db.Column(db.Text)
#     status = db.Column(db.Text, nullable=False, default='Pending')
#     hostel_no = db.Column(db.String(20), db.ForeignKey('hostel.hostel_no', ondelete='CASCADE'))
#     created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

#     applicant = db.relationship('CustomUser', backref=db.backref('guest_room_bookings', cascade='all, delete-orphan'))
#     hostel = db.relationship('Hostel', backref=db.backref('guest_room_bookings', cascade='all, delete-orphan'))
#     room = db.relationship('Room', backref=db.backref('guest_room_bookings', cascade='all, delete-orphan'))  # Add this relationship
class GuestRoomBooking(db.Model):
    __tablename__ = 'guest_room_booking'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('custom_user.id', ondelete='CASCADE'), nullable=False)
    room_no = db.Column(db.String(20), db.ForeignKey('room.room_no', ondelete='SET NULL'))
    total_guests = db.Column(db.Integer, nullable=False)
    guests_male = db.Column(db.Integer, nullable=False)
    guests_female = db.Column(db.Integer, nullable=False)
    guest_names = db.Column(db.Text, nullable=False)
    relation_with_applicant = db.Column(db.Text, nullable=False)
    guest_address = db.Column(db.Text, nullable=False)
    guest_contact = db.Column(db.Text, nullable=False)
    guest_email = db.Column(db.Text)
    purpose_of_visit = db.Column(db.Text, nullable=False)
    room_category = db.Column(db.Text, nullable=False)
    date_arrival = db.Column(db.Date, nullable=False)
    time_arrival = db.Column(db.Time, nullable=False)
    date_departure = db.Column(db.Date, nullable=False)
    time_departure = db.Column(db.Time, nullable=False)
    accommodation_by = db.Column(db.Text, nullable=False)
    remarks = db.Column(db.Text)
    status = db.Column(db.Text, nullable=False, default='Pending')
    hostel_no = db.Column(db.String(20), db.ForeignKey('hostel.hostel_no', ondelete='CASCADE'))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    payment_details = db.Column(JSON, nullable=True)  # Add this field to store payment details

    applicant = db.relationship('CustomUser', backref=db.backref('guest_room_bookings', cascade='all, delete-orphan'))
    hostel = db.relationship('Hostel', backref=db.backref('guest_room_bookings', cascade='all, delete-orphan'))
    room = db.relationship('Room', backref=db.backref('guest_room_bookings', cascade='all, delete-orphan'))

class ProjectAccommodationRequest(db.Model):
    __tablename__ = 'project_accommodation_request'
    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('custom_user.id', ondelete='CASCADE'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.faculty_id', ondelete='SET NULL'))
    address = db.Column(db.Text, nullable=False)
    stay_from = db.Column(db.Date, nullable=False)
    stay_to = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(1), nullable=False)  # 'A' or 'B'
    arrival_date = db.Column(db.Date, nullable=False)
    arrival_time = db.Column(db.Time, nullable=False)
    departure_date = db.Column(db.Date, nullable=False)
    departure_time = db.Column(db.Time, nullable=False)
    offer_letter_path = db.Column(db.String(200))
    id_proof_path = db.Column(db.String(200))
    remarks = db.Column(db.Text)
    hostel_allotted = db.Column(db.String(20), db.ForeignKey('hostel.hostel_no', ondelete='SET NULL'))
    status = db.Column(db.String(50))
    otp = db.Column(db.String(10))  # New column for OTP
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    applicant = db.relationship('CustomUser', backref=db.backref('project_accommodation_requests', cascade='all, delete-orphan'))
    hostel = db.relationship('Hostel', backref=db.backref('project_accommodation_requests', cascade='all, delete-orphan'))

class Guest(db.Model):
    __tablename__ = 'guest'
    guest_id = db.Column(db.Integer, db.ForeignKey('custom_user.id', ondelete='CASCADE'), primary_key=True)
    phone = db.Column(db.String(15))
    address = db.Column(db.String(255))


class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_email = db.Column(db.String(120), nullable=False)  # Email of the sender
    recipient_email = db.Column(db.String(120), nullable=False)  # Email of the recipient
    content = db.Column(db.Text, nullable=False)  # Message content
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp of the notification
    is_read = db.Column(db.Boolean, default=False)  # New field to track read status