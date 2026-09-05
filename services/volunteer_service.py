# backend/services/volunteer_service.py

from models.volunteer import VolunteerAssignment
from models.user import User
from models.event import Event
from extensions import db

class VolunteerService:

    @staticmethod
    def assign_volunteer(volunteer_id, event_id, duty=None):
        # Check volunteer exists and has correct role
        user = User.query.get(volunteer_id)
        if not user:
            return None, "User not found"
        if user.role != "volunteer":
            return None, "User is not a volunteer"

        # Check event exists
        event = Event.query.get(event_id)
        if not event:
            return None, "Event not found"

        # Check already assigned
        existing = VolunteerAssignment.query.filter_by(
            volunteer_id = volunteer_id,
            event_id     = event_id
        ).first()
        if existing:
            return None, "Volunteer already assigned to this event"

        assignment = VolunteerAssignment(
            volunteer_id = volunteer_id,
            event_id     = event_id,
            duty         = duty
        )
        db.session.add(assignment)
        db.session.commit()
        return assignment, None

    @staticmethod
    def get_event_volunteers(event_id):
        return VolunteerAssignment.query.filter_by(
            event_id = event_id
        ).all()

    @staticmethod
    def get_my_assignments(volunteer_id):
        return VolunteerAssignment.query.filter_by(
            volunteer_id = volunteer_id
        ).all()

    @staticmethod
    def remove_volunteer(volunteer_id, event_id):
        assignment = VolunteerAssignment.query.filter_by(
            volunteer_id = volunteer_id,
            event_id     = event_id
        ).first()
        if not assignment:
            return False, "Assignment not found"
        db.session.delete(assignment)
        db.session.commit()
        return True, None