from extensions import db
from datetime import datetime

class Checkin(db.Model):
    __tablename__ = "checkins"

    id              = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey("registrations.id"), unique=True, nullable=False)
    event_id        = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    volunteer_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    checked_in_at   = db.Column(db.DateTime, default=datetime.utcnow)

    registration = db.relationship("Registration", backref="checkin")

    def to_dict(self):
        from utils.ist import to_ist
        user = self.registration.user if self.registration else None
        return {
            "id":               self.id,
            "registration_id":  self.registration_id,
            "participant_name": user.name if user else "Unknown",
            "participant_email": user.email if user else "-",
            "event_id":         self.event_id,
            "volunteer_id":     self.volunteer_id,
            "checked_in_at":    to_ist(self.checked_in_at)
        }