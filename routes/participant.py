# backend/routes/participant.py

from flask import Blueprint, send_file
from middleware.auth_middleware import participant_required, get_current_user
from services.event_service import EventService
from services.registration_service import RegistrationService
from services.qr_service import QRService
from services.certificate_service import CertificateService
from flask_jwt_extended import get_jwt_identity
from utils.response import success, error

participant_bp = Blueprint("participant", __name__)


# ================================
# EVENTS
# ================================

@participant_bp.route("/events", methods=["GET"])
@participant_required
def get_published_events():
    events = EventService.get_published_events()
    # Only show non-completed events to participants
    active = [e for e in events if not e.is_completed]
    return success(data=[e.to_dict() for e in active])


@participant_bp.route("/events/<int:event_id>", methods=["GET"])
@participant_required
def get_event(event_id):
    event = EventService.get_event_by_id(event_id)
    if not event or not event.is_published:
        return error("Event not found", 404)
    return success(data=event.to_dict())


# ================================
# REGISTRATIONS
# ================================

@participant_bp.route("/events/<int:event_id>/register", methods=["POST"])
@participant_required
def register_for_event(event_id):
    user = get_current_user()
    reg, err = RegistrationService.register_participant(user.id, event_id)
    if err:
        return error(err)
    return success(
        message = "Registered successfully",
        data    = reg.to_dict(),
        status  = 201
    )


@participant_bp.route("/events/<int:event_id>/cancel", methods=["PUT"])
@participant_required
def cancel_registration(event_id):
    user = get_current_user()
    reg, err = RegistrationService.cancel_registration(user.id, event_id)
    if err:
        return error(err)
    return success(message="Registration cancelled", data=reg.to_dict())


@participant_bp.route("/registrations", methods=["GET"])
@participant_required
def my_registrations():
    user = get_current_user()
    regs = RegistrationService.get_my_registrations(user.id)
    return success(data=[r.to_dict() for r in regs])


# ================================
# QR CODE
# ================================

@participant_bp.route("/events/<int:event_id>/qr", methods=["GET"])
@participant_required
def download_qr(event_id):
    user_id = int(get_jwt_identity())
    buf, err = QRService.generate_qr(user_id, event_id)
    if err:
        return error(err, 404)
    return send_file(
        buf,
        mimetype      = "image/png",
        as_attachment = True,
        download_name = f"qr_{event_id}_{user_id}.png"
    )


# ================================
# CERTIFICATES
# ================================

@participant_bp.route("/events/<int:event_id>/certificate", methods=["GET"])
@participant_required
def get_certificate(event_id):
    user = get_current_user()
    cert, err = CertificateService.check_and_issue(user.id, event_id)
    if err:
        return error(err, 400)
    return success(data=cert.to_dict())


@participant_bp.route("/certificates", methods=["GET"])
@participant_required
def my_certificates():
    user = get_current_user()
    certs = CertificateService.get_my_certificates(user.id)
    return success(data=[c.to_dict() for c in certs])
