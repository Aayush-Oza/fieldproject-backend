# backend/services/certificate_service.py

from models.certificate import Certificate
from models.registration import Registration
from models.checkin import Checkin
from extensions import db
from datetime import datetime

class CertificateService:

    @staticmethod
    def check_and_issue(user_id, event_id):
        from models.event import Event
        from utils.ist import IST
        from datetime import datetime

        event = Event.query.get(event_id)
        if not event:
            return None, "Event not found"

        # Auto-check completion via IST
        now_ist = datetime.now(IST)
        event_end = datetime.combine(event.event_date, event.end_time).replace(tzinfo=IST)
        if not event.is_completed and now_ist < event_end:
            return None, "Event not yet completed"

        reg = Registration.query.filter_by(
            user_id=user_id, event_id=event_id, status="registered"
        ).first()
        if not reg:
            return None, "No registration found"

        checkin = Checkin.query.filter_by(
            registration_id=reg.id, event_id=event_id
        ).first()
        if not checkin:
            return None, "You were not checked in for this event"

        cert = Certificate.query.filter_by(
            user_id=user_id, event_id=event_id
        ).first()
        if cert:
            return cert, None

        cert = Certificate(
            user_id=user_id,
            event_id=event_id,
            registration_id=reg.id,
            is_eligible=True,
            issued_at=datetime.utcnow()
        )
        db.session.add(cert)
        db.session.commit()
        return cert, None

    @staticmethod
    def get_my_certificates(user_id):
        return Certificate.query.filter_by(
            user_id    = user_id,
            is_eligible = True
        ).all()