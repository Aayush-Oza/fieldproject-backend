# backend/routes/participant.py

from flask import Blueprint, jsonify, send_file
from middleware.auth_middleware import participant_required, get_current_user
from services.event_service import EventService
from services.registration_service import RegistrationService
from services.qr_service import QRService
from services.certificate_service import CertificateService
from flask_jwt_extended import get_jwt_identity
from utils.response import success, error
from io import BytesIO

participant_bp = Blueprint("participant", __name__)


# ════════════════════════════════════════════════
# EVENTS
# ════════════════════════════════════════════════

@participant_bp.route("/events", methods=["GET"])
@participant_required
def get_published_events():
    """
    Returns all published, non-completed events.
    Each event gets public dict — no private fields.
    """
    events = EventService.get_published_events()
    active = [e for e in events if not e.effective_is_completed]
    return success(data=[e.to_dict() for e in active])


@participant_bp.route("/events/<int:event_id>", methods=["GET"])
@participant_required
def get_event(event_id):
    """
    Single event detail.
    If participant is registered → return private dict (whatsapp, meet, contact).
    If not registered → return public dict only.
    """
    user  = get_current_user()
    event = EventService.get_event_by_id(event_id)

    if not event or not event.is_published:
        return error("Event not found", 404)

    reg = RegistrationService.get_registration(user.id, event_id)
    is_registered = reg is not None and reg.status == "registered"

    if is_registered:
        return success(data=event.to_private_dict())
    return success(data=event.to_dict())


# ════════════════════════════════════════════════
# REGISTRATIONS
# ════════════════════════════════════════════════

@participant_bp.route("/events/<int:event_id>/register", methods=["POST"])
@participant_required
def register_for_event(event_id):
    """
    Register participant for an event.
    Checks:
    - Event exists and is published
    - Event is not completed
    - Registration is still open (deadline check)
    - Participant not already registered
    - Event not full
    After registration → QR generated and uploaded to S3.
    """
    user  = get_current_user()
    event = EventService.get_event_by_id(event_id)

    if not event or not event.is_published:
        return error("Event not found", 404)

    if event.effective_is_completed:
        return error("This event has already completed")

    if not event.registration_open:
        return error("Registration is closed for this event")

    reg, err = RegistrationService.register_participant(user.id, event_id)
    if err:
        return error(err)

    return success(
        message="Registered successfully",
        data=reg.to_dict(),
        status=201
    )


@participant_bp.route("/registrations", methods=["GET"])
@participant_required
def my_registrations():
    """
    All registrations of current participant.
    Each registration includes private event details
    since they are already registered.
    """
    user = get_current_user()
    regs = RegistrationService.get_my_registrations(user.id)

    data = []
    for reg in regs:
        reg_dict = reg.to_dict()
        if reg.event:
            reg_dict["event"] = reg.event.to_private_dict()
        data.append(reg_dict)

    return success(data=data)


@participant_bp.route("/registrations/<int:event_id>", methods=["GET"])
@participant_required
def get_my_registration(event_id):
    """
    Single registration detail for a specific event.
    Returns private event dict since participant is registered.
    """
    user = get_current_user()
    reg  = RegistrationService.get_registration(user.id, event_id)

    if not reg:
        return error("Registration not found", 404)

    reg_dict = reg.to_dict()
    if reg.event:
        reg_dict["event"] = reg.event.to_private_dict()

    return success(data=reg_dict)


# ════════════════════════════════════════════════
# QR CODE
# ════════════════════════════════════════════════

@participant_bp.route("/events/<int:event_id>/qr", methods=["GET"])
@participant_required
def get_qr(event_id):
    user = get_current_user()
    reg  = RegistrationService.get_registration(user.id, event_id)

    if not reg or reg.status != "registered":
        return error("No active registration found", 404)

    url, err = QRService.get_qr_url(reg)
    if err:
        return error(f"Could not load QR: {err}", 500)

    return success(data={
        "qr_url":   url,
        "qr_token": reg.qr_token,
        "event_id": event_id,
    })


# ════════════════════════════════════════════════
# CERTIFICATES
# ════════════════════════════════════════════════

@participant_bp.route("/events/<int:event_id>/certificate", methods=["GET"])
@participant_required
def get_certificate(event_id):
    """
    Check eligibility and issue certificate if eligible.
    Participant must have checked in to be eligible.
    """
    user  = get_current_user()
    event = EventService.get_event_by_id(event_id)

    if not event:
        return error("Event not found", 404)

    if not event.effective_is_completed:
        return error("Certificate will be available after the event completes")

    cert, err = CertificateService.check_and_issue(user.id, event_id)
    if err:
        return error(err, 400)

    return success(data=cert.to_dict())


@participant_bp.route("/certificates", methods=["GET"])
@participant_required
def my_certificates():
    """All certificates earned by current participant."""
    user  = get_current_user()
    certs = CertificateService.get_my_certificates(user.id)
    return success(data=[c.to_dict() for c in certs])


@participant_bp.route("/events/<int:event_id>/certificate/download", methods=["GET"])
@participant_required
def download_certificate(event_id):
    """
    Generate and stream a PDF certificate for the participant.

    Flow:
    1. Check event exists and is completed.
    2. Ensure certificate has been issued (check_and_issue handles idempotency).
    3. Generate PDF via ReportLab.
    4. Stream back as attachment — browser triggers download directly.

    No S3 needed — generated on the fly, lightweight (<50 KB).
    """
    user  = get_current_user()
    event = EventService.get_event_by_id(event_id)

    if not event:
        return error("Event not found", 404)

    if not event.effective_is_completed:
        return error("Certificate will be available after the event completes", 400)

    # Issue cert if not already issued (idempotent)
    cert, err = CertificateService.check_and_issue(user.id, event_id)
    if err:
        return error(err, 400)

    # Generate PDF
    pdf_bytes, filename, err = CertificateService.generate_pdf(user.id, event_id)
    if err:
        return error(f"Could not generate certificate: {err}", 500)

    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )