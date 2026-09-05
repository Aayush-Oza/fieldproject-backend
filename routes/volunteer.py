# backend/routes/volunteer.py

from flask import Blueprint, request
from middleware.auth_middleware import volunteer_required, get_current_user
from services.checkin_service import CheckinService
from services.event_service import EventService
from services.volunteer_service import VolunteerService
from utils.response import success, error

volunteer_bp = Blueprint("volunteer", __name__)


# ================================
# MY ASSIGNMENTS
# ================================

@volunteer_bp.route("/assignments", methods=["GET"])
@volunteer_required
def my_assignments():
    user        = get_current_user()
    assignments = VolunteerService.get_my_assignments(user.id)
    return success(data=[a.to_dict() for a in assignments])


@volunteer_bp.route("/assignments/<int:event_id>/event", methods=["GET"])
@volunteer_required
def get_assigned_event(event_id):
    user = get_current_user()

    # Check volunteer is assigned to this event
    assignments = VolunteerService.get_my_assignments(user.id)
    assigned_event_ids = [a.event_id for a in assignments]
    if event_id not in assigned_event_ids:
        return error("You are not assigned to this event", 403)

    event = EventService.get_event_by_id(event_id)
    if not event:
        return error("Event not found", 404)
    return success(data=event.to_dict())


# ================================
# CHECK-IN
# ================================

@volunteer_bp.route("/checkin", methods=["POST"])
@volunteer_required
def checkin_participant():
    user = get_current_user()
    data = request.get_json()

    if not data:
        return error("No data provided")

    qr_token = data.get("qr_token")
    event_id = data.get("event_id")

    if not qr_token or not event_id:
        return error("qr_token and event_id are required")

    checkin, err = CheckinService.checkin_by_token(
        qr_token     = qr_token,
        volunteer_id = user.id,
        event_id     = int(event_id)
    )
    if err:
        return error(err)

    return success(
        message = "Participant checked in successfully",
        data    = checkin.to_dict(),
        status  = 201
    )


@volunteer_bp.route("/checkin/<int:event_id>/log", methods=["GET"])
@volunteer_required
def checkin_log(event_id):
    user = get_current_user()

    # Verify assigned
    assignments = VolunteerService.get_my_assignments(user.id)
    assigned_event_ids = [a.event_id for a in assignments]
    if event_id not in assigned_event_ids:
        return error("You are not assigned to this event", 403)

    checkins = CheckinService.get_event_checkins(event_id)
    return success(data=[c.to_dict() for c in checkins])