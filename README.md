# Summer Internship & Accommodation Management Portal

A centralized web-based system designed to streamline the workflow for summer internship applications, guest room bookings, and project accommodations at IIT Ropar. This portal enables smooth interaction between students, faculty, HODs, and hostel administration with automated approvals, email notifications, and status tracking.

## 🚀 Features

- Student form submission for:
  - Summer Internships
  - Guest Room Reservations
  - Project Accommodations
- Role-based dashboards for:
  - Faculty (Email-based approvals)
  - HODs (Dashboard approvals)
  - Admins (AR HM, JA HM)
  - Chief Warden (Final approvals)
- Email & OTP-based secure approval flow
- Hostel room allocation by JA HM
- Real-time status updates via notifications

## 🔒 Access Constraints

- **Students**: Login only with `@iitrpr.ac.in` email
- **Faculty/HODs**: Access through institutional email (email-based links with OTP)
- **Admins**: Secure dashboard login with system-generated credentials

## 👥 Stakeholders

- Students
- Faculty
- HODs
- JA HM (Junior Assistant Hostel Management)
- AR HM (Assistant Registrar Hostel Management)
- Chief Warden

## 🔧 Technologies Used

- Frontend: HTML, CSS, JavaScript (React recommended)
- Backend: Node.js, Express.js
- Database: MongoDB / PostgreSQL
- Email Service: Nodemailer / SMTP
- OTP & Auth: Custom token-based auth
- Deployment: (e.g., Heroku / Render / Railway)

## 📈 Future Enhancements

- Integration of secure **payment gateway**
- **SMS notifications** for real-time alerts

## 🙏 Acknowledgements

Special thanks to:
- TAs and mentors for constant guidance
- IT section for support during deployment
- Hostel and academic authorities for providing workflow insights
- IIT Ropar for the opportunity to build this impactful project

## 📬 Contact

For any queries, contact the development team or drop an email at `support@hostelportal.in`.

---

## Commands to run the code

   ## create the virtual environment & activate
   python3 -m venv venv
   source venv/bin/activate

   ## Install Dependencied
   pip install requirements.txt

   ## Run Command
   flask run
