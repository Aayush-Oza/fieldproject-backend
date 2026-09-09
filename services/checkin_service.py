# backend/services/checkin_service.py

from models.checkin import Checkin
from models.registration import Registration
from models.volunteer import VolunteerAssignment
from models.event import Event
from extensions import db
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

class CheckinService:

    @staticmethod
    def checkin_by_token(qr_token, volunteer_id, event_id):
        # Validate volunteer is assigned to this event
        assignment = VolunteerAssignment.query.filter_by(
            volunteer_id = volunteer_id,
            event_id     = event_id
        ).first()
        if not assignment:
            return None, "You are not assigned to this event"

        # Time window check
        event = Event.query.get(event_id)
        if not event:
            return None, "Event not found"

        now_ist     = datetime.now(IST)
        event_start = datetime.combine(event.event_date, event.start_time).replace(tzinfo=IST)
        event_end   = datetime.combine(event.event_date, event.end_time).replace(tzinfo=IST)
        window_open = event_start - timedelta(hours=1)

        if now_ist < window_open:
            return None, f"Check-in opens at {window_open.strftime('%I:%M %p IST')}"
        if now_ist > event_end:
            return None, "Event has already ended"

        # Find registration by QR token
        reg = Registration.query.filter_by(
            qr_token = qr_token,
            status   = "registered"
        ).first()
        if not reg:
            return None, "Invalid or cancelled QR token"

        # Check registration belongs to this event
        if reg.event_id != event_id:
            return None, "QR code is for a different event"

        # Check already checked in
        existing = Checkin.query.filter_by(
            registration_id = reg.id
        ).first()
        if existing:
            return None, "Participant already checked in"

        # Create checkin
        checkin = Checkin(
            registration_id = reg.id,
            event_id        = event_id,
            volunteer_id    = volunteer_id
        )
        db.session.add(checkin)
        db.session.commit()
        return checkin, None

    @staticmethod
    def get_event_checkins(event_id):
        return Checkin.query.filter_by(
            event_id = event_id
        ).order_by(Checkin.checked_in_at.desc()).all()

    @staticmethod
    def get_my_checkins(volunteer_id):
        return Checkin.query.filter_by(
            volunteer_id = volunteer_id
        ).order_by(Checkin.checked_in_at.desc()).all()