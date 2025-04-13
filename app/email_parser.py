import imaplib
import email
from email.header import decode_header
from redis import Redis
from redis.exceptions import LockError
from app.models import ProjectAccommodationRequest, Faculty
from app.database import db
from app import create_app, mail
from flask_mail import Message
import re

EMAIL_USER = 'johnDoe18262117@gmail.com'
EMAIL_PASS = 'avsj hgzp mxfc yxxz'

# Redis client for distributed locking
redis_client = Redis()

def check_email():
    try:
        mail_server = imaplib.IMAP4_SSL("imap.gmail.com")
        mail_server.login(EMAIL_USER, EMAIL_PASS)
        mail_server.select("inbox")

        # Only emails replying to accommodation approval
        status, messages = mail_server.search(None, 'SUBJECT "Re: New Project Accommodation Request for Approval"')
        if status != "OK" or not messages[0]:
            print("📭 No relevant emails found.")
            return

        app = create_app()
        with app.app_context():
            for msg_id in messages[0].split():
                status, msg_data = mail_server.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                for part in msg_data:
                    if not isinstance(part, tuple):
                        continue

                    msg = email.message_from_bytes(part[1])

                    # Decode subject
                    subject = decode_header(msg["Subject"])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(errors="ignore")
                    print(f"📨 Subject: {subject.strip()}")

                    # Decode body
                    body = ""
                    if msg.is_multipart():
                        for p in msg.walk():
                            if p.get_content_type() == "text/plain" and "attachment" not in str(p.get("Content-Disposition")):
                                payload = p.get_payload(decode=True)
                                if payload:
                                    body = payload.decode(errors="ignore")
                                break
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            body = payload.decode(errors="ignore")

                    if not body:
                        print("⚠️ No body found in message.")
                        continue

                    body_lower = body.lower()
                    print(f"📝 Body Preview: {body_lower.strip()[:100]}...")

                    # Match commands
                    patterns = {
                        "faculty_approve": "faculty approves request #",
                        "faculty_reject": "faculty rejects request #",
                        "hod_approve": "hod approves request #",
                        "hod_reject": "hod rejects request #"
                    }

                    for action, keyword in patterns.items():
                        if keyword in body_lower:
                            try:
                                request_id = int(body_lower.split(keyword)[1].split()[0])
                                process_request(action, request_id)
                            except (IndexError, ValueError):
                                print(f"⚠️ Failed to extract request ID from body: {body_lower.strip()}")
                            break

        mail_server.logout()

    except Exception as e:
        print(f"💥 Email parsing failed: {e}")


def process_request(action, request_id):
    lock_key = f"request_lock_{request_id}"
    try:
        # Acquire a lock for the specific request ID
        with redis_client.lock(lock_key, timeout=10):  # Lock expires after 10 seconds
            if action == "faculty_approve":
                handle_faculty_approval(request_id, approved=True)
            elif action == "faculty_reject":
                handle_faculty_approval(request_id, approved=False)
            elif action == "hod_approve":
                handle_hod_approval(request_id, approved=True)
            elif action == "hod_reject":
                handle_hod_approval(request_id, approved=False)
    except LockError:
        print(f"⚠️ Could not acquire lock for request #{request_id}. Task skipped.")


def handle_faculty_approval(request_id, approved):
    try:
        request_entry = ProjectAccommodationRequest.query.get(request_id)
        if not request_entry:
            print(f"❌ Request #{request_id} not found.")
            return

        print(f"ℹ️ Current status for #{request_id}: '{request_entry.status}'")

        if request_entry.status.strip().lower() != "pending approval from faculty":
            print(f"⚠️ Faculty step skipped for #{request_id}. Current status: '{request_entry.status}'")
            return

        if approved:
            request_entry.status = "Pending approval from HOD"
            db.session.commit()
            print(f"✅ Request #{request_id} moved to HOD.")

            # Email HOD
            hod = Faculty.query.filter_by(is_hod=True).first()
            if hod:
                msg = Message(
                    subject="New Project Accommodation Request for Approval",
                    sender=EMAIL_USER,
                    recipients=[hod.user.email]
                )
                msg.body = (
                    f"Dear {hod.user.name},\n\n"
                    f"Request #{request_id} has been approved by Faculty and is now pending your review.\n\n"
                    f"Reply with:\n"
                    f"HOD Approves Request #{request_id}\n"
                    f"OR\n"
                    f"HOD Rejects Request #{request_id}\n\n"
                    f"Thank you."
                )
                mail.send(msg)
                print(f"📧 Sent to HOD: {hod.user.email}")
        else:
            request_entry.status = "Rejected by Faculty"
            db.session.commit()
            print(f"❌ Request #{request_id} rejected by Faculty.")
    except Exception as e:
        db.session.rollback()
        print(f"💥 Error handling faculty approval for #{request_id}: {e}")


def handle_hod_approval(request_id, approved):
    try:
        request_entry = ProjectAccommodationRequest.query.get(request_id)
        if not request_entry:
            print(f"❌ Request #{request_id} not found.")
            return

        print(f"ℹ️ Current status for #{request_id}: '{request_entry.status}'")

        if request_entry.status.strip().lower() != "pending approval from hod":
            print(f"⚠️ HOD step skipped for #{request_id}. Current status: '{request_entry.status}'")
            return

        if approved:
            request_entry.status = "Pending approval from AR (HM)"
        else:
            request_entry.status = "Rejected by HOD"

        db.session.commit()
        print(f"✅ Request #{request_id} → {'Approved' if approved else 'Rejected'} by HOD.")
    except Exception as e:
        db.session.rollback()
        print(f"💥 Error handling HOD approval for #{request_id}: {e}")