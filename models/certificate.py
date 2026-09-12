from extensions import db
from datetime import datetime

class Certificate(db.Model):
    __tablename__ = "certificates"

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id        = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    registration_id = db.Column(db.Integer, db.ForeignKey("registrations.id"), nullable=False)
    is_eligible     = db.Column(db.Boolean, default=False)
    issued_at       = db.Column(db.DateTime, nullable=True)
    generated_at    = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    user         = db.relationship("User", backref="certificates")
    registration = db.relationship("Registration", backref="certificate")
    event = db.relationship("Event", backref="certificates")

    def to_dict(self):
        return {
            "id":              self.id,
            "user_id":         self.user_id,
            "event_id":        self.event_id,
            "registration_id": self.registration_id,
            "is_eligible":     self.is_eligible,
            "issued_at":       self.issued_at.isoformat() if self.issued_at else None,
            "generated_at":    self.generated_at.isoformat(),
            "event_title":     self.event.title if self.event else None  # ← add this
        }