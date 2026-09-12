from extensions import db
from datetime import datetime

class VolunteerAssignment(db.Model):
    __tablename__ = "volunteer_assignments"

    id           = db.Column(db.Integer, primary_key=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id     = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    duty         = db.Column(db.String(100), nullable=True)
    assigned_at  = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        db.UniqueConstraint("volunteer_id", "event_id", name="unique_volunteer_event"),
    )

    volunteer = db.relationship("User", foreign_keys=[volunteer_id], overlaps="user,volunteer_assignments")

    def to_dict(self):
        return {
            "id":             self.id,
            "volunteer_id":   self.volunteer_id,
            "volunteer_name": self.volunteer.name if self.volunteer else "Unnamed",
            "volunteer_email": self.volunteer.email if self.volunteer else "-",
            "event_id":       self.event_id,
            "duty":           self.duty,
            "assigned_at": self.assigned_at.isoformat()
        }