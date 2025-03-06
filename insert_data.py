from app import create_app
from app.database import db
from app.models import CustomUser, Student, Faculty, Caretaker, Admin, Hostel, Room, Warden, Batch, InternshipApplication, CaretakerHistory
from datetime import datetime

app = create_app()

with app.app_context():
    db.create_all()

    users = [
        CustomUser(id=1, email='2022csb1125+student1@iitrpr.ac.in', name='student1', password='123', is_staff=False, is_active=True, gender='Male'),
        CustomUser(id=2, email='2022csb1125+student2@iitrpr.ac.in', name='student2', password='123', is_staff=False, is_active=True, gender='Female'),
        CustomUser(id=3, email='2022csb1125+student3@iitrpr.ac.in', name='student3', password='123', is_staff=False, is_active=True, gender='Male'),
        CustomUser(id=4, email='2022csb1125+student4@iitrpr.ac.in', name='student4', password='123', is_staff=False, is_active=True, gender='Female'),
        CustomUser(id=5, email='2022csb1125+faculty1@iitrpr.ac.in', name='faculty1', password='123', is_staff=True, is_active=True, gender='Male'),
        CustomUser(id=6, email='2022csb1125+faculty2@iitrpr.ac.in', name='faculty2', password='123', is_staff=True, is_active=True, gender='Female'),
        CustomUser(id=7, email='2022csb1125+faculty3@iitrpr.ac.in', name='faculty3', password='123', is_staff=True, is_active=True, gender='Male'),
        CustomUser(id=8, email='2022csb1125+faculty4@iitrpr.ac.in', name='faculty4', password='123', is_staff=True, is_active=True, gender='Female'),
        CustomUser(id=9, email='2022csb1125+caretaker1@iitrpr.ac.in', name='caretaker1', password='123', is_staff=True, is_active=True, gender='Male'),
        CustomUser(id=10, email='2022csb1125+caretaker2@iitrpr.ac.in', name='caretaker2', password='123', is_staff=True, is_active=True, gender='Female'),
        CustomUser(id=11, email='2022csb1125+caretaker3@iitrpr.ac.in', name='caretaker3', password='123', is_staff=True, is_active=True, gender='Male'),
        CustomUser(id=12, email='2022csb1125+caretaker4@iitrpr.ac.in', name='caretaker4', password='123', is_staff=True, is_active=True, gender='Female'),
        CustomUser(id=13, email='2022csb1125+admin1@iitrpr.ac.in', name='admin1', password='123', is_staff=True, is_active=True, gender='Male'),
        CustomUser(id=14, email='2022csb1125+admin2@iitrpr.ac.in', name='admin2', password='123', is_staff=True, is_active=True, gender='Female'),
        CustomUser(id=15, email='2022csb1125+admin3@iitrpr.ac.in', name='admin3', password='123', is_staff=True, is_active=True, gender='Male'),
        CustomUser(id=16, email='2022csb1125+admin4@iitrpr.ac.in', name='admin4', password='123', is_staff=True, is_active=True, gender='Female')
    ]
    db.session.bulk_save_objects(users)
    db.session.commit()

    students = [
        Student(student_id=1, department='Computer Science Engineering', student_phone='9876543210', student_roll='2024CSB1125', student_year=1, student_room_no='CE-111', student_batch='B.Tech 2024'),
        Student(student_id=2, department='Electrical Engineering', student_phone='9876543210', student_roll='2023EEB1125', student_year=2, student_room_no='CW-111', student_batch='B.Tech 2023'),
        Student(student_id=3, department='Mechanical Engineering', student_phone='9876543210', student_roll='2022MEB1125', student_year=3, student_room_no='BE-111', student_batch='B.Tech 2022'),
        Student(student_id=4, department='Civil Engineering', student_phone='9876543210', student_roll='2021CEB1125', student_year=4, student_room_no='BW-111', student_batch='B.Tech 2021')
    ]
    db.session.bulk_save_objects(students)
    db.session.commit()

    faculties = [
        Faculty(faculty_id=5, department='Computer Science Engineering', faculty_phone='0123456789', is_hod=False, signature=b'faculty1_signature'),
        Faculty(faculty_id=6, department='Electrical Engineering', faculty_phone='1123456789', is_hod=True, signature=b'faculty2_signature'),
        Faculty(faculty_id=7, department='Mechanical Engineering', faculty_phone='2123456789', is_hod=False, signature=b'faculty3_signature'),
        Faculty(faculty_id=8, department='Civil Engineering', faculty_phone='3123456789', is_hod=False, signature=b'faculty4_signature')
    ]
    db.session.bulk_save_objects(faculties)
    db.session.commit()

    caretakers = [
        Caretaker(caretaker_id=1, user_id=9, hostel_no='CH'),
        Caretaker(caretaker_id=2, user_id=10, hostel_no='RA'),
        Caretaker(caretaker_id=3, user_id=11, hostel_no='SU'),
        Caretaker(caretaker_id=4, user_id=12, hostel_no='BR')
    ]
    db.session.bulk_save_objects(caretakers)
    db.session.commit()

    admins = [
        Admin(admin_id=13, phone='9234567899', signature=b'admin1_signature'),
        Admin(admin_id=14, phone='9234567898', signature=b'admin2_signature'),
        Admin(admin_id=15, phone='9234567897', signature=b'admin3_signature'),
        Admin(admin_id=16, phone='9234567896', signature=b'admin4_signature')
    ]
    db.session.bulk_save_objects(admins)
    db.session.commit()

    hostels = [
        Hostel(hostel_no='CH', hostel_name='Chenab', hostel_type='Boys', num_floors=4, capacity=400),
        Hostel(hostel_no='RA', hostel_name='Raavi', hostel_type='Girls', num_floors=4, capacity=200),
        Hostel(hostel_no='SU', hostel_name='Sutlej', hostel_type='Boys', num_floors=4, capacity=400),
        Hostel(hostel_no='BR', hostel_name='Bhramaputra', hostel_type='Mixed', num_floors=6, capacity=900)
    ]
    db.session.bulk_save_objects(hostels)
    db.session.commit()

    rooms = [
        Room(room_no='CW-101', floor=1, hostel_no='CH', room_occupancy=2, current_occupancy=2),
        Room(room_no='CE-102', floor=1, hostel_no='CH', room_occupancy=2, current_occupancy=1),
        Room(room_no='CW-103', floor=1, hostel_no='CH', room_occupancy=2, current_occupancy=0),
        Room(room_no='CE-201', floor=2, hostel_no='CH', room_occupancy=2, current_occupancy=2),
        Room(room_no='CW-202', floor=2, hostel_no='CH', room_occupancy=2, current_occupancy=1),
        Room(room_no='CE-203', floor=2, hostel_no='CH', room_occupancy=2, current_occupancy=0),
        Room(room_no='RW-101', floor=1, hostel_no='RA', room_occupancy=2, current_occupancy=2),
        Room(room_no='RE-102', floor=1, hostel_no='RA', room_occupancy=2, current_occupancy=1),
        Room(room_no='RW-103', floor=1, hostel_no='RA', room_occupancy=2, current_occupancy=0),
        Room(room_no='RE-201', floor=2, hostel_no='RA', room_occupancy=2, current_occupancy=2),
        Room(room_no='RW-202', floor=2, hostel_no='RA', room_occupancy=2, current_occupancy=1),
        Room(room_no='RE-203', floor=2, hostel_no='RA', room_occupancy=2, current_occupancy=0),
        Room(room_no='SW-101', floor=1, hostel_no='SU', room_occupancy=2, current_occupancy=2),
        Room(room_no='SE-102', floor=1, hostel_no='SU', room_occupancy=2, current_occupancy=1),
        Room(room_no='SW-103', floor=1, hostel_no='SU', room_occupancy=2, current_occupancy=0),
        Room(room_no='SE-201', floor=2, hostel_no='SU', room_occupancy=2, current_occupancy=2),
        Room(room_no='SW-202', floor=2, hostel_no='SU', room_occupancy=2, current_occupancy=1),
        Room(room_no='SE-203', floor=2, hostel_no='SU', room_occupancy=2, current_occupancy=0),
        Room(room_no='BW-101', floor=1, hostel_no='BR', room_occupancy=2, current_occupancy=2),
        Room(room_no='BE-102', floor=1, hostel_no='BR', room_occupancy=2, current_occupancy=1),
        Room(room_no='BW-103', floor=1, hostel_no='BR', room_occupancy=2, current_occupancy=0),
        Room(room_no='BE-201', floor=2, hostel_no='BR', room_occupancy=2, current_occupancy=2),
        Room(room_no='BW-202', floor=2, hostel_no='BR', room_occupancy=2, current_occupancy=1),
        Room(room_no='BE-203', floor=2, hostel_no='BR', room_occupancy=2, current_occupancy=0)
    ]
    db.session.bulk_save_objects(rooms)
    db.session.commit()

    wardens = [
        Warden(warden_id=1, faculty_id=7, hostel_no='CH', is_chief=False),
        Warden(warden_id=2, faculty_id=8, hostel_no='RA', is_chief=True)
    ]
    db.session.bulk_save_objects(wardens)
    db.session.commit()

    batches = [
        Batch(batch_no='B.Tech 2024', number_of_students=550, number_of_girls=70, number_of_boys=480),
        Batch(batch_no='B.Tech 2023', number_of_students=500, number_of_girls=60, number_of_boys=440),
        Batch(batch_no='B.Tech 2022', number_of_students=450, number_of_girls=50, number_of_boys=400),
        Batch(batch_no='B.Tech 2021', number_of_students=400, number_of_girls=40, number_of_boys=360)
    ]
    db.session.bulk_save_objects(batches)
    db.session.commit()

    # applications = [
    #     InternshipApplication(
    #         id=1, name='Ashutosh Singh', gender='Male', affiliation='XYZ University', address='123 Street, City', 
    #         contact_number='9876543210', email='2022csb1132+student@iitrpr.ac.in', faculty_mentor='Dr. Rajesh Kumar', 
    #         faculty_email='2022csb1132+hod@iitrpr.ac.in', arrival_date=datetime.strptime('2025-03-01', '%Y-%m-%d').date(), 
    #         departure_date=datetime.strptime('2025-06-01', '%Y-%m-%d').date(), id_card='Ashutosh_Singh_Internship_Certificate.png', 
    #         official_letter='letter.pdf', remarks='Waiting for approval', status='Pending Faculty Approval', 
    #         faculty_signature_id=2, hod_signature_id=2, admin_signature_id=4
    #     )
    # ]
    # db.session.bulk_save_objects(applications)
    # db.session.commit()

    # caretaker_histories = [
    #     CaretakerHistory(caretaker_id=1, hostel_no='SU', start_date=datetime.strptime('2023-01-01', '%Y-%m-%d'), end_date=None)
    # ]
    # db.session.bulk_save_objects(caretaker_histories)
    # db.session.commit()