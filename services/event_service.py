# backend/services/event_service.py

from models.event import Event
from models.checkin import Checkin
from models.registration import Registration
from extensions import db
from datetime import datetime


class EventService:

    # ──────────────────────────────────────────────────
    # CREATE
    # ──────────────────────────────────────────────────
    @staticmethod
    def create_event(data, admin_id):
        try:
            # ── Required ──
            event_date = datetime.strptime(data["event_date"], "%Y-%m-%d").date()
            start_time = datetime.strptime(data["start_time"], "%H:%M").time()
            end_time   = datetime.strptime(data["end_time"],   "%H:%M").time()

            # ── Registration deadline (optional) ──
            registration_deadline = None
            if data.get("registration_deadline"):
                registration_deadline = datetime.strptime(
                    data["registration_deadline"], "%Y-%m-%dT%H:%M"
                )

            event = Event(
                # Core
                title        = data["title"].strip(),
                description  = data.get("description", "").strip(),
                venue        = data["venue"].strip(),
                capacity     = int(data["capacity"]),
                event_date   = event_date,
                start_time   = start_time,
                end_time     = end_time,
                is_published = data.get("is_published", False),
                created_by   = admin_id,

                # Identity
                event_type     = data.get("event_type",     None),
                mode           = data.get("mode",           None),
                organizer_dept = (data.get("organizer_dept") or "").strip() or None,
                speaker_name   = (data.get("speaker_name")   or "").strip() or None,
                tags           = (data.get("tags")           or "").strip() or None,

                # Media
                banner_url = data.get("banner_url", None),

                # Registration control
                registration_deadline = registration_deadline,
                has_certificate       = data.get("has_certificate", False),
                is_paid               = data.get("is_paid",         False),
                entry_fee             = float(data["entry_fee"]) if data.get("entry_fee") else None,

                # Private
                whatsapp_link  = (data.get("whatsapp_link")  or "").strip() or None,
                meet_link      = (data.get("meet_link")      or "").strip() or None,
                contact_name   = (data.get("contact_name")   or "").strip() or None,
                contact_phone  = (data.get("contact_phone")  or "").strip() or None,
                venue_map_link = (data.get("venue_map_link") or "").strip() or None,
            )

            db.session.add(event)
            db.session.commit()
            return event, None

        except ValueError as e:
            return None, f"Invalid data format: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"Could not create event: {str(e)}"

    # ──────────────────────────────────────────────────
    # READ
    # ──────────────────────────────────────────────────
    @staticmethod
    def get_all_events():
        """Admin — all events, newest first."""
        return Event.query.order_by(Event.created_at.desc()).all()

    @staticmethod
    def get_published_events():
        """
        Participant — published events only.
        Completion is checked via effective_is_completed property (time-based).
        We fetch all published and let the property filter in route.
        """
        return Event.query.filter_by(
            is_published=True
        ).order_by(Event.event_date.asc()).all()

    @staticmethod
    def get_event_by_id(event_id):
        return Event.query.get(event_id)

    # ──────────────────────────────────────────────────
    # UPDATE
    # ──────────────────────────────────────────────────
    @staticmethod
    def get_edit_permission(event):
        """
        Returns (can_edit, allowed_fields, reason)

        Rules:
        - Completed            → no edit at all
        - Published + <24 hrs  → no edit at all
        - Published + >24 hrs  → only soft fields
        - Unpublished          → all fields
        """
        if event.effective_is_completed:
            return False, [], "Event is completed"

        if event.is_published:
            if event.hours_until_event <= 24:
                return False, [], "Event is within 24 hours, no edits allowed"

            # Soft fields only — things that don't affect participant commitment
            soft_fields = [
                "description",
                "speaker_name",
                "organizer_dept",
                "tags",
                "banner_url",
                "whatsapp_link",
                "meet_link",
                "contact_name",
                "contact_phone",
                "venue_map_link",
                "has_certificate",
                "is_paid",
                "entry_fee",
            ]
            return True, soft_fields, "Published — only soft fields editable"

        # Unpublished — all fields allowed
        all_fields = [
            "title", "description", "venue", "capacity",
            "event_date", "start_time", "end_time",
            "event_type", "mode", "organizer_dept", "speaker_name", "tags",
            "banner_url", "registration_deadline",
            "has_certificate", "is_paid", "entry_fee",
            "whatsapp_link", "meet_link", "contact_name",
            "contact_phone", "venue_map_link",
            "is_published",
        ]
        return True, all_fields, "Unpublished — all fields editable"

    @staticmethod
    def update_event(event_id, data):
        event = Event.query.get(event_id)
        if not event:
            return None, "Event not found"

        can_edit, allowed_fields, reason = EventService.get_edit_permission(event)

        if not can_edit:
            return None, reason

        # Only apply allowed fields
        for field in allowed_fields:
            if field not in data:
                continue

            # ── Datetime fields need parsing ──
            if field == "event_date":
                try:
                    setattr(event, field, datetime.strptime(data[field], "%Y-%m-%d").date())
                except ValueError:
                    return None, "Invalid event_date format. Use YYYY-MM-DD"

            elif field in ("start_time", "end_time"):
                try:
                    setattr(event, field, datetime.strptime(data[field], "%H:%M").time())
                except ValueError:
                    return None, f"Invalid {field} format. Use HH:MM"

            elif field == "registration_deadline":
                try:
                    if data[field]:
                        setattr(event, field, datetime.strptime(data[field], "%Y-%m-%dT%H:%M"))
                    else:
                        setattr(event, field, None)
                except ValueError:
                    return None, "Invalid registration_deadline format. Use YYYY-MM-DDTHH:MM"

            elif field == "capacity":
                setattr(event, field, int(data[field]))

            elif field == "entry_fee":
                setattr(event, field, float(data[field]) if data[field] else None)

            elif field in ("is_published", "is_completed", "has_certificate", "is_paid"):
                setattr(event, field, bool(data[field]))

            else:
                # String fields — strip and set None if empty
                val = str(data[field]).strip() if data[field] else None
                setattr(event, field, val)

        event.updated_at = datetime.now()
        db.session.commit()
        return event, None

    # ──────────────────────────────────────────────────
    # DELETE
    # ──────────────────────────────────────────────────
    @staticmethod
    def delete_event(event_id):
        event = Event.query.get(event_id)
        if not event:
            return False, "Event not found"
        db.session.delete(event)
        db.session.commit()
        return True, None

    # ──────────────────────────────────────────────────
    # STATS
    # ──────────────────────────────────────────────────
    @staticmethod
    def get_event_stats(event_id):
        event = Event.query.get(event_id)
        if not event:
            return None, "Event not found"

        total_registered = Registration.query.filter_by(
            event_id=event_id,
            status="registered"
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
            "is_completed":      event.effective_is_completed,
            "registration_open": event.registration_open,
            "status": (
                "full" if occupancy_percent >= 100 else
                "near" if occupancy_percent >= 80  else
                "safe"
            )
        }, None