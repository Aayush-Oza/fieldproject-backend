# backend/services/certificate_service.py

from models.certificate import Certificate
from models.registration import Registration
from models.checkin import Checkin
from extensions import db
from datetime import datetime

class CertificateService:

    @staticmethod
    def check_and_issue(user_id, event_id):
        # Get registration
        reg = Registration.query.filter_by(
            user_id  = user_id,
            event_id = event_id,
            status   = "registered"
        ).first()
        if not reg:
            return None, "No registration found"

        # Check if checked in
        checkin = Checkin.query.filter_by(
            registration_id = reg.id,
            event_id        = event_id
        ).first()
        if not checkin:
            return None, "You were not checked in for this event"

        # Check if certificate already exists
        cert = Certificate.query.filter_by(
            user_id  = user_id,
            event_id = event_id
        ).first()

        if cert:
            return cert, None  # Already issued

        # Issue new certificate
        cert = Certificate(
            user_id         = user_id,
            event_id        = event_id,
            registration_id = reg.id,
            is_eligible     = True,
            issued_at       = datetime.utcnow()
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