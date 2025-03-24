from app import create_app
from app.database import db
from app.models import DummyBatch, DummyHostel, DummyAllocation

app = create_app()

with app.app_context():
    db.create_all()

    batches = [
        DummyBatch(batch_no='B.Tech 2024', number_of_students=550, number_of_boys=480, number_of_girls=70),
        DummyBatch(batch_no='B.Tech 2023', number_of_students=500, number_of_boys=440, number_of_girls=60),
        DummyBatch(batch_no='B.Tech 2022', number_of_students=450, number_of_boys=400, number_of_girls=50),
        DummyBatch(batch_no='B.Tech 2021', number_of_students=400, number_of_boys=360, number_of_girls=40)
    ]
    db.session.bulk_save_objects(batches)
    db.session.commit()

    hostels = [
        DummyHostel(hostel_no='CH', hostel_name='Chenab', hostel_type='Boys', capacity=400),
        DummyHostel(hostel_no='RA', hostel_name='Raavi', hostel_type='Girls', capacity=250),
        DummyHostel(hostel_no='SU', hostel_name='Sutlej', hostel_type='Boys', capacity=400),
        DummyHostel(hostel_no='BR', hostel_name='Bhramaputra', hostel_type='Boys', capacity=900)
    ]
    db.session.bulk_save_objects(hostels)
    db.session.commit()

    allocations = [
        DummyAllocation(batch_id=1, hostel_id=1, number_of_students=100),  # Boys
        DummyAllocation(batch_id=1, hostel_id=2, number_of_students=70),   # Girls
        DummyAllocation(batch_id=2, hostel_id=1, number_of_students=200),  # Boys
        DummyAllocation(batch_id=2, hostel_id=2, number_of_students=60),   # Girls
        DummyAllocation(batch_id=3, hostel_id=1, number_of_students=150),  # Boys
        DummyAllocation(batch_id=3, hostel_id=2, number_of_students=50),   # Girls
        DummyAllocation(batch_id=4, hostel_id=1, number_of_students=100),  # Boys
        DummyAllocation(batch_id=4, hostel_id=2, number_of_students=40)    # Girls
    ]
    db.session.bulk_save_objects(allocations)
    db.session.commit()