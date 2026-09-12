# Standalone scheduler — runs separately from gunicorn
from app import create_app
from apscheduler.schedulers.blocking import BlockingScheduler

app = create_app()

def auto_complete_events():
    from models.event import Event
    from models.checkin import Checkin
    from services.certificate_service import CertificateService
    from datetime import datetime

    with app.app_context():
        now = datetime.now()
        events = Event.query.filter_by(is_completed=False, is_published=True).all()
        for event in events:
            from datetime import timedelta
            event_end = datetime.combine(event.event_date, event.end_time)
            if event.end_time < event.start_time:
                event_end += timedelta(days=1)
            if now > event_end:
                event.is_completed = True
                from extensions import db
                db.session.commit()
                print(f"[scheduler] Marked complete: {event.title}")
                checkins = Checkin.query.filter_by(event_id=event.id).all()
                for c in checkins:
                    if c.registration:
                        CertificateService.check_and_issue(c.registration.user_id, event.id)

scheduler = BlockingScheduler()
scheduler.add_job(auto_complete_events, 'interval', minutes=5)
print("[scheduler] Starting...")
auto_complete_events()  # run once immediately on start
scheduler.start()