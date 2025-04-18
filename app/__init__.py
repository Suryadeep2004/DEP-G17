from flask import Flask
import os
from .config import Config
from .database import db
from flask_mail import Mail
from flask_migrate import Migrate
import base64

mail = Mail()
migrate = Migrate()

def create_app():
    app = Flask(__name__, template_folder=os.path.join(os.getcwd(), "templates"), static_folder=os.path.join(os.getcwd(), "static"))
    app.config.from_object(Config)

    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    from app.index import index_bp
    app.register_blueprint(index_bp)

    from app.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.student import student_bp
    app.register_blueprint(student_bp)

    from app.caretaker import caretaker_bp
    app.register_blueprint(caretaker_bp)

    from app.faculty import faculty_bp
    app.register_blueprint(faculty_bp)

    from app.admin import admin_bp
    app.register_blueprint(admin_bp)

    from app.guest import guest_bp
    app.register_blueprint(guest_bp)


    @app.template_filter('b64encode')
    def b64encode_filter(data):
        if data:
            return base64.b64encode(data).decode('utf-8')
        return None

    return app