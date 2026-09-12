from flask import Flask
from config import Config
from extensions import db, bcrypt, jwt, socketio, cors
from apscheduler.schedulers.background import BackgroundScheduler

from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.volunteer import volunteer_bp
from routes.participant import participant_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": Config.FRONTEND_URL}})
    socketio.init_app(app)

    app.register_blueprint(auth_bp,        url_prefix="/api/auth")
    app.register_blueprint(admin_bp,       url_prefix="/api/admin")
    app.register_blueprint(volunteer_bp,   url_prefix="/api/volunteer")
    app.register_blueprint(participant_bp, url_prefix="/api/participant")

    import sockets.occupancy  # noqa: F401

    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    with app.app_context():
        db.create_all()

    # ── Scheduler ──────────────────────────────
    def auto_complete_events():
        from models.event import Event
        from models.checkin import Checkin
        from services.certificate_service import CertificateService
        from datetime import datetime

        with app.app_context():
            now = datetime.now()
            events = Event.query.filter_by(is_completed=False, is_published=True).all()
            for event in events:
                event_end = datetime.combine(event.event_date, event.end_time)
                if now > event_end:
                    event.is_completed = True
                    db.session.commit()
                    checkins = Checkin.query.filter_by(event_id=event.id).all()
                    for c in checkins:
                        if c.registration:
                            CertificateService.check_and_issue(c.registration.user_id, event.id)

    scheduler = BackgroundScheduler()
    scheduler.add_job(auto_complete_events, 'interval', minutes=5)
    scheduler.start()
    # ───────────────────────────────────────────

    return app


if __name__ == "__main__":
    app = create_app()
    socketio.run(
        app,
        debug=Config.FLASK_DEBUG,
        port=Config.FLASK_PORT
    )