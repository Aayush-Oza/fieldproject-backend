from extensions import db
from datetime import datetime
import uuid

class Registration(db.Model):
    __tablename__ = "registrations"

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id      = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    qr_token      = db.Column(db.String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    status        = db.Column(db.Enum("registered", "cancelled", name="registration_status"), default="registered")
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "event_id", name="unique_user_event"),
    )

    user = db.relationship("User", foreign_keys=[user_id], overlaps="registrations")

    def to_dict(self):
        from utils.ist import to_ist
        d = {
            "id":            self.id,
            "user_id":       self.user_id,
            "event_id":      self.event_id,
            "qr_token":      self.qr_token,
            "status":        self.status,
            "registered_at": to_ist(self.registered_at)
        }
        if self.event:
            d["event"] = self.event.to_dict()
        return d