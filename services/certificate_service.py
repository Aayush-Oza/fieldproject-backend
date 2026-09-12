# backend/services/certificate_service.py

from models.certificate import Certificate
from models.registration import Registration
from models.checkin import Checkin
from extensions import db
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


class CertificateService:

    # ════════════════════════════════════════════════
    # CHECK & ISSUE
    # ════════════════════════════════════════════════

    @staticmethod
    def check_and_issue(user_id, event_id):
        from models.event import Event

        event = Event.query.get(event_id)
        if not event:
            return None, "Event not found"

        if not event.effective_is_completed:
            return None, "Event not yet completed"

        reg = Registration.query.filter_by(
            user_id=user_id, event_id=event_id, status="registered"
        ).first()
        if not reg:
            return None, "No registration found"

        checkin = Checkin.query.filter_by(
            registration_id=reg.id, event_id=event_id
        ).first()
        if not checkin:
            return None, "You were not checked in for this event"

        # Return existing cert if already issued
        cert = Certificate.query.filter_by(user_id=user_id, event_id=event_id).first()
        if cert:
            return cert, None

        cert = Certificate(
            user_id=user_id,
            event_id=event_id,
            registration_id=reg.id,
            is_eligible=True,
            issued_at=datetime.now()
        )
        db.session.add(cert)
        db.session.commit()
        return cert, None

    # ════════════════════════════════════════════════
    # GET ALL CERTIFICATES FOR USER
    # ════════════════════════════════════════════════

    @staticmethod
    def get_my_certificates(user_id):
        return Certificate.query.filter_by(
            user_id=user_id,
            is_eligible=True
        ).all()

    # ════════════════════════════════════════════════
    # GENERATE PDF
    # ════════════════════════════════════════════════

    @staticmethod
    def generate_pdf(user_id, event_id):
        """
        Generate a professional certificate PDF using ReportLab.
        Returns (pdf_bytes, filename, error).
        Caller must verify eligibility before calling this.
        """
        from models.event import Event
        from models.user import User

        user  = User.query.get(user_id)
        event = Event.query.get(event_id)
        cert  = Certificate.query.filter_by(user_id=user_id, event_id=event_id, is_eligible=True).first()

        if not user or not event or not cert:
            return None, None, "Certificate not found"

        try:
            pdf_bytes = CertificateService._build_pdf(
                participant_name=user.name,
                event_title=event.title,
                event_type=event.event_type,
                event_date=event.event_date,
                venue=event.venue,
                speaker_name=event.speaker_name,
                organizer_dept=event.organizer_dept,
                mode=event.mode,
                issued_at=cert.issued_at,
            )
            safe_title = "".join(c for c in event.title if c.isalnum() or c in (" ", "-", "_")).strip()
            filename = f"Certificate_{safe_title}_{user.name}.pdf".replace(" ", "_")
            return pdf_bytes, filename, None

        except Exception as e:
            return None, None, str(e)

    # ════════════════════════════════════════════════
    # INTERNAL: BUILD PDF BYTES
    # ════════════════════════════════════════════════

    @staticmethod
    def _build_pdf(
        participant_name,
        event_title,
        event_type,
        event_date,
        venue,
        speaker_name,
        organizer_dept,
        mode,
        issued_at,
    ):
        buffer = BytesIO()
        W, H = landscape(A4)
        c = canvas.Canvas(buffer, pagesize=landscape(A4))

        # ── Background: very light navy tint ──────────────────────
        c.setFillColorRGB(0.97, 0.975, 0.99)
        c.rect(0, 0, W, H, fill=1, stroke=0)

        # ── Outer border (navy) ───────────────────────────────────
        c.setStrokeColorRGB(0.12, 0.25, 0.55)
        c.setLineWidth(3)
        c.rect(12 * mm, 12 * mm, W - 24 * mm, H - 24 * mm, fill=0, stroke=1)

        # ── Inner border (gold) ───────────────────────────────────
        c.setStrokeColorRGB(0.75, 0.62, 0.25)
        c.setLineWidth(1.2)
        c.rect(16 * mm, 16 * mm, W - 32 * mm, H - 32 * mm, fill=0, stroke=1)

        # ── Top navy bar ──────────────────────────────────────────
        c.setFillColorRGB(0.12, 0.25, 0.55)
        c.rect(16 * mm, H - 16 * mm - 18 * mm, W - 32 * mm, 18 * mm, fill=1, stroke=0)

        # ── Header text inside top bar (gold) ─────────────────────
        c.setFillColorRGB(0.95, 0.83, 0.35)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(
            W / 2,
            H - 16 * mm - 12 * mm,
            "E V E N T O P S   ·   CERTIFICATE OF PARTICIPATION",
        )

        # ── Thin gold divider under bar ───────────────────────────
        c.setStrokeColorRGB(0.75, 0.62, 0.25)
        c.setLineWidth(0.5)
        c.line(30 * mm, H - 38 * mm, W - 30 * mm, H - 38 * mm)

        # ── Main title ────────────────────────────────────────────
        c.setFillColorRGB(0.12, 0.25, 0.55)
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(W / 2, H - 60 * mm, "Certificate of Participation")

        # ── "This is to certify that" ─────────────────────────────
        c.setFont("Helvetica", 11)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawCentredString(W / 2, H - 70 * mm, "This is to certify that")

        # ── Participant name ──────────────────────────────────────
        c.setFillColorRGB(0.08, 0.18, 0.42)
        c.setFont("Helvetica-Bold", 26)
        c.drawCentredString(W / 2, H - 86 * mm, participant_name)

        # ── Gold underline beneath name ───────────────────────────
        name_w = c.stringWidth(participant_name, "Helvetica-Bold", 26)
        c.setStrokeColorRGB(0.75, 0.62, 0.25)
        c.setLineWidth(1)
        c.line(W / 2 - name_w / 2, H - 88 * mm, W / 2 + name_w / 2, H - 88 * mm)

        # ── "has successfully participated in" ────────────────────
        c.setFont("Helvetica", 11)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawCentredString(W / 2, H - 98 * mm, "has successfully participated in")

        # ── Event title ───────────────────────────────────────────
        c.setFont("Helvetica-Bold", 18)
        c.setFillColorRGB(0.10, 0.22, 0.50)
        c.drawCentredString(W / 2, H - 112 * mm, event_title)

        # ── Event meta: type · mode · venue ───────────────────────
        meta_parts = []
        if event_type:  meta_parts.append(event_type.title())
        if mode:        meta_parts.append(mode.title())
        if venue:       meta_parts.append(venue)
        if meta_parts:
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0.45, 0.45, 0.45)
            c.drawCentredString(W / 2, H - 121 * mm, "  ·  ".join(meta_parts))

        # ── Speaker / dept ────────────────────────────────────────
        sub_parts = []
        if speaker_name:   sub_parts.append(f"Speaker: {speaker_name}")
        if organizer_dept: sub_parts.append(f"Organised by: {organizer_dept}")
        if sub_parts:
            c.setFont("Helvetica-Oblique", 10)
            c.setFillColorRGB(0.45, 0.45, 0.45)
            c.drawCentredString(W / 2, H - 129 * mm, "  ·  ".join(sub_parts))

        # ── Gold divider ──────────────────────────────────────────
        c.setStrokeColorRGB(0.75, 0.62, 0.25)
        c.setLineWidth(0.5)
        c.line(40 * mm, H - 140 * mm, W - 40 * mm, H - 140 * mm)

        # ── Footer: event date (left) · issued date (right) ───────
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.5, 0.5, 0.5)

        if event_date:
            date_str = (
                event_date.strftime("%d %B %Y")
                if hasattr(event_date, "strftime")
                else str(event_date)
            )
            c.drawString(30 * mm, H - 150 * mm, f"Event Date: {date_str}")

        if issued_at:
            issued_str = (
                issued_at.strftime("%d %B %Y")
                if hasattr(issued_at, "strftime")
                else str(issued_at)
            )
            c.drawRightString(W - 30 * mm, H - 150 * mm, f"Issued on: {issued_str}")

        # ── Bottom navy bar ───────────────────────────────────────
        c.setFillColorRGB(0.12, 0.25, 0.55)
        c.rect(16 * mm, 16 * mm, W - 32 * mm, 10 * mm, fill=1, stroke=0)

        c.setFillColorRGB(0.95, 0.83, 0.35)
        c.setFont("Helvetica", 8)
        c.drawCentredString(
            W / 2, 20 * mm,
            "Generated by EventOps  ·  Automated Certificate System"
        )

        c.save()
        buffer.seek(0)
        return buffer.read()