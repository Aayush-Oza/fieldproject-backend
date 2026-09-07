# services/occupancy_service.py

from models.checkin import Checkin
from models.event import Event


class OccupancyService:

    @staticmethod
    def get_live_occupancy(event_id: int) -> dict:
        """Return current checkin count and fill rate for an event."""
        event = Event.query.get(event_id)
        if not event:
            return None

        checkin_count = Checkin.query.filter_by(event_id=event_id).count()
        fill_rate     = round((checkin_count / event.capacity) * 100, 1) if event.capacity else 0

        return {
            "event_id":     event_id,
            "event_title":  event.title,
            "capacity":     event.capacity,
            "checkin_count": checkin_count,
            "fill_rate_pct": fill_rate,
            "is_full":      checkin_count >= event.capacity,
        }

    @staticmethod
    def get_all_live_occupancy() -> list:
        from datetime import datetime, timezone, timedelta
        IST = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(IST)

        events = Event.query.filter_by(is_published=True).all()
        result = []
        for event in events:
            # Skip if completed (DB flag or time-based)
            event_end = datetime.combine(event.event_date, event.end_time).replace(tzinfo=timezone.utc)
            if event.is_completed or now_ist > event_end:
                continue

            checkin_count = Checkin.query.filter_by(event_id=event.id).count()
            fill_rate     = round((checkin_count / event.capacity) * 100, 1) if event.capacity else 0
            result.append({
                "event_id":      event.id,
                "event_title":   event.title,
                "capacity":      event.capacity,
                "checkin_count": checkin_count,
                "fill_rate_pct": fill_rate,
                "is_full":       checkin_count >= event.capacity,
            })
        return result