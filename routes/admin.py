# backend/routes/admin.py

from flask import Blueprint, request
from middleware.auth_middleware import admin_required, get_current_user
from services.event_service import EventService
from services.volunteer_service import VolunteerService
from services.occupancy_service import OccupancyService
from services.forecast_service import predict_attendance, predict_attendance_from_dict, get_model_status
from utils.response import success, error
from models.user import User
from extensions import db


admin_bp = Blueprint("admin", __name__)


# ════════════════════════════════════════════════
# EVENT MANAGEMENT
# ════════════════════════════════════════════════

@admin_bp.route("/events", methods=["GET"])
@admin_required
def get_all_events():
    events = EventService.get_all_events()
    return success(data=[e.to_dict() for e in events])


@admin_bp.route("/events", methods=["POST"])
@admin_required
def create_event():
    data  = request.get_json()
    admin = get_current_user()

    if not data:
        return error("No data provided")

    required = ["title", "venue", "capacity", "event_date", "start_time", "end_time"]
    for field in required:
        if not data.get(field):
            return error(f"{field} is required")

    event, err = EventService.create_event(data, admin.id)
    if err:
        return error(err)

    return success(
        message = "Event created successfully",
        data    = event.to_dict(),
        status  = 201
    )


@admin_bp.route("/events/<int:event_id>", methods=["GET"])
@admin_required
def get_event(event_id):
    event = EventService.get_event_by_id(event_id)
    if not event:
        return error("Event not found", 404)
    return success(data=event.to_dict())


@admin_bp.route("/events/<int:event_id>/edit-info", methods=["GET"])
@admin_required
def get_edit_info(event_id):
    """
    Returns whether admin can edit this event and which fields are allowed.
    Frontend uses this to disable/enable form fields before showing edit form.
    """
    event = EventService.get_event_by_id(event_id)
    if not event:
        return error("Event not found", 404)

    can_edit, allowed_fields, reason = EventService.get_edit_permission(event)
    return success(data={
        "can_edit":       can_edit,
        "allowed_fields": allowed_fields,
        "reason":         reason,
        "hours_until":    round(event.hours_until_event, 2),
        "is_completed":   event.effective_is_completed,
    })


@admin_bp.route("/events/<int:event_id>", methods=["PUT"])
@admin_required
def update_event(event_id):
    data = request.get_json()
    if not data:
        return error("No data provided")

    event, err = EventService.update_event(event_id, data)
    if err:
        return error(err)  # 400 by default — could be permission or not found

    return success(
        message = "Event updated successfully",
        data    = event.to_dict()
    )


@admin_bp.route("/events/<int:event_id>", methods=["DELETE"])
@admin_required
def delete_event(event_id):
    done, err = EventService.delete_event(event_id)
    if err:
        return error(err, 404)
    return success(message="Event deleted successfully")


@admin_bp.route("/events/<int:event_id>/stats", methods=["GET"])
@admin_required
def event_stats(event_id):
    stats, err = EventService.get_event_stats(event_id)
    if err:
        return error(err, 404)
    return success(data=stats)


@admin_bp.route("/events/<int:event_id>/publish", methods=["PUT"])
@admin_required
def toggle_publish(event_id):
    event = EventService.get_event_by_id(event_id)
    if not event:
        return error("Event not found", 404)

    # Cannot publish a completed event
    if not event.is_published and event.effective_is_completed:
        return error("Cannot publish a completed event")

    event, err = EventService.update_event(
        event_id,
        {"is_published": not event.is_published}
    )
    if err:
        return error(err)

    return success(
        message = f"Event {'published' if event.is_published else 'unpublished'}",
        data    = event.to_dict()
    )


# ════════════════════════════════════════════════
# VOLUNTEER MANAGEMENT
# ════════════════════════════════════════════════

@admin_bp.route("/events/<int:event_id>/volunteers", methods=["GET"])
@admin_required
def get_event_volunteers(event_id):
    volunteers = VolunteerService.get_event_volunteers(event_id)
    return success(data=[v.to_dict() for v in volunteers])


@admin_bp.route("/events/<int:event_id>/volunteers", methods=["POST"])
@admin_required
def assign_volunteer(event_id):
    data = request.get_json()
    if not data or not data.get("volunteer_id"):
        return error("volunteer_id is required")

    assignment, err = VolunteerService.assign_volunteer(
        volunteer_id = data["volunteer_id"],
        event_id     = event_id,
        duty         = data.get("duty", None)
    )
    if err:
        return error(err)

    return success(
        message = "Volunteer assigned successfully",
        data    = assignment.to_dict(),
        status  = 201
    )


@admin_bp.route("/events/<int:event_id>/volunteers/<int:volunteer_id>", methods=["DELETE"])
@admin_required
def remove_volunteer(event_id, volunteer_id):
    done, err = VolunteerService.remove_volunteer(volunteer_id, event_id)
    if err:
        return error(err, 404)
    return success(message="Volunteer removed successfully")


# ════════════════════════════════════════════════
# USER MANAGEMENT
# ════════════════════════════════════════════════

@admin_bp.route("/users", methods=["GET"])
@admin_required
def get_all_users():
    users = User.query.all()
    return success(data=[u.to_dict() for u in users])


@admin_bp.route("/users/<int:user_id>/make-volunteer", methods=["PUT"])
@admin_required
def make_volunteer(user_id):
    user = User.query.get(user_id)
    if not user:
        return error("User not found", 404)
    if user.role == "admin":
        return error("Cannot change admin role")
    if user.role == "volunteer":
        return error("User is already a volunteer")

    user.role = "volunteer"
    db.session.commit()
    return success(
        message = "User promoted to volunteer",
        data    = user.to_dict()
    )


@admin_bp.route("/users/<int:user_id>/make-participant", methods=["PUT"])
@admin_required
def make_participant(user_id):
    user = User.query.get(user_id)
    if not user:
        return error("User not found", 404)
    if user.role == "admin":
        return error("Cannot change admin role")

    user.role = "participant"
    db.session.commit()
    return success(
        message = "User changed to participant",
        data    = user.to_dict()
    )


# ════════════════════════════════════════════════
# FORECAST ROUTES
# ════════════════════════════════════════════════

@admin_bp.route("/forecast/status", methods=["GET"])
@admin_required
def forecast_status():
    status = get_model_status()
    return success(data=status)


@admin_bp.route("/forecast/events/<int:event_id>", methods=["GET"])
@admin_required
def forecast_event(event_id):
    from models.event import Event
    event = Event.query.get(event_id)
    if not event:
        return error("Event not found", 404)

    try:
        result = predict_attendance(event)
        return success(data=result)
    except FileNotFoundError:
        return error("Model not trained yet. Run python -m ai.train", 503)


@admin_bp.route("/forecast/preview", methods=["POST"])
@admin_required
def forecast_preview():
    data = request.get_json()
    required = ["capacity", "event_date", "start_time", "end_time"]
    for field in required:
        if not data.get(field):
            return error(f"{field} is required")

    try:
        result = predict_attendance_from_dict(data)
        return success(data=result)
    except FileNotFoundError:
        return error("Model not trained yet. Run python -m ai.train", 503)
    except Exception as e:
        return error(str(e))


# ════════════════════════════════════════════════
# OCCUPANCY ROUTES
# ════════════════════════════════════════════════

@admin_bp.route("/occupancy", methods=["GET"])
@admin_required
def get_all_occupancy():
    data = OccupancyService.get_all_live_occupancy()
    return success(data=data)


@admin_bp.route("/occupancy/<int:event_id>", methods=["GET"])
@admin_required
def get_event_occupancy(event_id):
    data = OccupancyService.get_live_occupancy(event_id)
    if not data:
        return error("Event not found", 404)
    return success(data=data)


# ════════════════════════════════════════════════
# CERTIFICATES
# ════════════════════════════════════════════════

@admin_bp.route("/certificates/count", methods=["GET"])
@admin_required
def get_certificate_count():
    from models.certificate import Certificate
    count = Certificate.query.filter_by(is_eligible=True).count()
    return success(data={"count": count})