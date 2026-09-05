# backend/services/event_service.py

from models.event import Event
from models.checkin import Checkin
from models.registration import Registration
from extensions import db
from datetime import datetime

class EventService:

    @staticmethod
    def create_event(data, admin_id):
        event = Event(
            title        = data["title"],
            description  = data.get("description", ""),
            venue        = data["venue"],
            capacity     = int(data["capacity"]),
            event_date   = datetime.strptime(data["event_date"], "%Y-%m-%d").date(),
            start_time   = datetime.strptime(data["start_time"], "%H:%M").time(),
            end_time     = datetime.strptime(data["end_time"], "%H:%M").time(),
            is_published = data.get("is_published", False),
            created_by   = admin_id
        )
        db.session.add(event)
        db.session.commit()
        return event, None

    @staticmethod
    def get_all_events():
        return Event.query.order_by(Event.created_at.desc()).all()

    @staticmethod
    def get_published_events():
        return Event.query.filter_by(
            is_published=True,
            is_completed=False
        ).order_by(Event.event_date.asc()).all()

    @staticmethod
    def get_event_by_id(event_id):
        return Event.query.get(event_id)

    @staticmethod
    def update_event(event_id, data):
        event = Event.query.get(event_id)
        if not event:
            return None, "Event not found"

        if "title"        in data: event.title        = data["title"]
        if "description"  in data: event.description  = data["description"]
        if "venue"        in data: event.venue         = data["venue"]
        if "capacity"     in data: event.capacity      = int(data["capacity"])
        if "is_published" in data: event.is_published  = data["is_published"]
        if "is_completed" in data: event.is_completed  = data["is_completed"]
        if "event_date"   in data:
            event.event_date = datetime.strptime(data["event_date"], "%Y-%m-%d").date()
        if "start_time"   in data:
            event.start_time = datetime.strptime(data["start_time"], "%H:%M").time()
        if "end_time"     in data:
            event.end_time = datetime.strptime(data["end_time"], "%H:%M").time()

        event.updated_at = datetime.utcnow()
        db.session.commit()
        return event, None

    @staticmethod
    def delete_event(event_id):
        event = Event.query.get(event_id)
        if not event:
            return False, "Event not found"
        db.session.delete(event)
        db.session.commit()
        return True, None

    @staticmethod
    def get_event_stats(event_id):
        event = Event.query.get(event_id)
        if not event:
            return None, "Event not found"

        total_registered = Registration.query.filter_by(
            event_id = event_id,
            status   = "registered"
        ).count()

        total_checkedin = Checkin.query.filter_by(
            event_id=event_id
        ).count()

        occupancy_percent = round(
            (total_checkedin / event.capacity) * 100, 2
        ) if event.capacity > 0 else 0

        return {
            "event_id":          event_id,
            "title":             event.title,
            "capacity":          event.capacity,
            "total_registered":  total_registered,
            "total_checkedin":   total_checkedin,
            "occupancy_percent": occupancy_percent,
            "status": (
                "full"    if occupancy_percent >= 100 else
                "near"    if occupancy_percent >= 80  else
                "safe"
            )
        }, None