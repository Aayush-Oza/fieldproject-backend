# backend/models/registration.py

from extensions import db
from datetime import datetime
import uuid


class Registration(db.Model):
    __tablename__ = "registrations"

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id      = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    qr_token      = db.Column(db.String(100), unique=True, nullable=False,
                               default=lambda: str(uuid.uuid4()))
    qr_s3_key     = db.Column(db.String(500), nullable=True)   # S3 object key — added
    status        = db.Column(
                        db.Enum("registered", "cancelled", name="registration_status"),
                        default="registered"
                    )
    registered_at = db.Column(db.DateTime, default=datetime.now)  # was utcnow — fixed

    __table_args__ = (
        db.UniqueConstraint("user_id", "event_id", name="unique_user_event"),
    )

    def to_dict(self):
        return {
            "id":            self.id,
            "user_id":       self.user_id,
            "event_id":      self.event_id,
            "qr_token":      self.qr_token,
            "qr_s3_key":     self.qr_s3_key,
            "status":        self.status,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            # event dict attached in route layer (public or private depending on context)
        }