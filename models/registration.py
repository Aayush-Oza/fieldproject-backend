from extensions import db
from datetime import datetime
import uuid

class Registration(db.Model):
    __tablename__ = "registrations"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id     = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    qr_token     = db.Column(db.String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    status = db.Column(db.Enum("registered", "cancelled", name="registration_status"), default="registered")
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint - one registration per user per event
    __table_args__ = (
        db.UniqueConstraint("user_id", "event_id", name="unique_user_event"),
    )

    def to_dict(self):
        d = {
            "id":            self.id,
            "user_id":       self.user_id,
            "event_id":      self.event_id,
            "qr_token":      self.qr_token,
            "status":        self.status,
            "registered_at": self.registered_at.isoformat()
        }
    # Include nested event if loaded
        if self.event:
            d["event"] = self.event.to_dict()
        return d