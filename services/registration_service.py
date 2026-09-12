# backend/services/registration_service.py

from models.registration import Registration
from models.event import Event
from extensions import db
from services.qr_service import QRService


class RegistrationService:

    @staticmethod
    def register_participant(user_id, event_id):
        # Check event exists and is published
        event = Event.query.get(event_id)
        if not event:
            return None, "Event not found"
        if not event.is_published:
            return None, "Event is not open for registration"
        if event.effective_is_completed:
            return None, "Event is already completed"

        # Check duplicate
        existing = Registration.query.filter_by(
            user_id  = user_id,
            event_id = event_id
        ).first()
        # after
        if existing:
            return None, "Already registered for this event"

        # Check capacity
        registered_count = Registration.query.filter_by(
            event_id = event_id,
            status   = "registered"
        ).count()
        if registered_count >= event.capacity:
            return None, "Event is at full capacity"

        # Create registration
        reg = Registration(
            user_id  = user_id,
            event_id = event_id
        )
        db.session.add(reg)
        db.session.commit()
        s3_key, err = QRService.generate_and_upload(reg)
        if not err:
            reg.qr_s3_key = s3_key
        db.session.commit()
        return reg, None

    @staticmethod
    def get_my_registrations(user_id):
        return Registration.query.filter_by(
            user_id = user_id
        ).order_by(Registration.registered_at.desc()).all()

    @staticmethod
    def get_registration_by_token(qr_token):
        return Registration.query.filter_by(qr_token=qr_token).first()
    
    @staticmethod
    def get_registration(user_id, event_id):
        return Registration.query.filter_by(
            user_id  = user_id,
            event_id = event_id,
            status   = "registered"
        ).first()