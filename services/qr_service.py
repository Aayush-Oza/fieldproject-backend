# backend/services/qr_service.py

import qrcode
import io
from models.registration import Registration

class QRService:

    @staticmethod
    def generate_qr(user_id, event_id):
        print(f"[QR] Looking for user_id={user_id} event_id={event_id}")
        reg = Registration.query.filter_by(
            user_id  = user_id,
            event_id = event_id,
            status   = "registered"
        ).first()
        print(f"[QR] Found: {reg}")
        if not reg:
            return None, "Registration not found or cancelled"

        qr = qrcode.QRCode(
            version          = 1,
            error_correction = qrcode.constants.ERROR_CORRECT_H,
            box_size         = 10,
            border           = 4
        )
        qr.add_data(reg.qr_token)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf, None

    @staticmethod
    def validate_token(qr_token):
        reg = Registration.query.filter_by(
            qr_token = qr_token,
            status   = "registered"
        ).first()
        if not reg:
            return None, "Invalid or cancelled QR token"
        return reg, None