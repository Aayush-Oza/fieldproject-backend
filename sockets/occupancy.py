# sockets/occupancy.py

from flask_socketio import emit, join_room, leave_room
from extensions import socketio
from services.occupancy_service import OccupancyService


# ─── Client joins a specific event room ───────────────────────────────────────

@socketio.on("join_event")
def handle_join(data):
    """
    Client sends: { event_id: 1 }
    Server adds client to room "event_1" and sends current occupancy.
    """
    event_id = data.get("event_id")
    if not event_id:
        emit("error", {"message": "event_id required"})
        return

    room = f"event_{event_id}"
    join_room(room)

    occupancy = OccupancyService.get_live_occupancy(event_id)
    if occupancy:
        emit("occupancy_update", occupancy, to=room)
    else:
        emit("error", {"message": "Event not found"})


# ─── Client leaves an event room ──────────────────────────────────────────────

@socketio.on("leave_event")
def handle_leave(data):
    """Client sends: { event_id: 1 }"""
    event_id = data.get("event_id")
    if event_id:
        leave_room(f"event_{event_id}")


# ─── Client requests a manual refresh ─────────────────────────────────────────

@socketio.on("request_occupancy")
def handle_request(data):
    """
    Client sends: { event_id: 1 }
    Useful for manual pull instead of waiting for push.
    """
    event_id = data.get("event_id")
    if not event_id:
        emit("error", {"message": "event_id required"})
        return

    occupancy = OccupancyService.get_live_occupancy(event_id)
    if occupancy:
        emit("occupancy_update", occupancy)
    else:
        emit("error", {"message": "Event not found"})


# ─── Admin joins dashboard room to watch all events ───────────────────────────

@socketio.on("join_dashboard")
def handle_join_dashboard():
    """Admin joins 'admin_dashboard' room to receive all-event updates."""
    join_room("admin_dashboard")
    all_occupancy = OccupancyService.get_all_live_occupancy()
    emit("dashboard_update", {"events": all_occupancy})


# ─── Utility: push update after every checkin ─────────────────────────────────
# Call this from checkin_service.py after a successful checkin.

def emit_occupancy_update(event_id: int):
    """
    Called internally (not by client) after a new checkin.
    Broadcasts updated occupancy to all clients watching that event
    and to the admin dashboard room.
    """
    occupancy = OccupancyService.get_live_occupancy(event_id)
    if not occupancy:
        return

    # Push to event-specific room
    socketio.emit("occupancy_update", occupancy, to=f"event_{event_id}")

    # Push to admin dashboard
    all_occupancy = OccupancyService.get_all_live_occupancy()
    socketio.emit("dashboard_update", {"events": all_occupancy}, to="admin_dashboard")