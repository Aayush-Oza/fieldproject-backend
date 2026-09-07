from extensions import db
from datetime import datetime

class Event(db.Model):
    __tablename__ = "events"

    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(200), nullable=False)
    description  = db.Column(db.Text, nullable=True)
    venue        = db.Column(db.String(200), nullable=False)
    capacity     = db.Column(db.Integer, nullable=False)
    event_date   = db.Column(db.Date, nullable=False)
    start_time   = db.Column(db.Time, nullable=False)
    end_time     = db.Column(db.Time, nullable=False)
    is_published = db.Column(db.Boolean, default=False)
    is_completed = db.Column(db.Boolean, default=False)
    created_by   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    registrations        = db.relationship("Registration", backref="event", lazy=True)
    checkins             = db.relationship("Checkin", backref="event", lazy=True)
    volunteer_assignment = db.relationship("VolunteerAssignment", backref="event", lazy=True)
    certificates         = db.relationship("Certificate", backref="event", lazy=True)

    def to_dict(self):
        from datetime import datetime, timezone, timedelta
        IST = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(IST)
        event_end = datetime.combine(self.event_date, self.end_time).replace(tzinfo=timezone.utc)
        is_completed = self.is_completed or (now_ist > event_end)

        return {
            "id":                 self.id,
            "title":              self.title,
            "description":        self.description,
            "venue":              self.venue,
            "capacity":           self.capacity,
            "event_date":         self.event_date.isoformat(),
            "start_time":         str(self.start_time),
            "end_time":           str(self.end_time),
            "is_published":       self.is_published,
            "is_completed":       is_completed,
            "created_by":         self.created_by,
            "created_at":         self.created_at.isoformat(),
            "registration_count": len([r for r in self.registrations if r.status == "registered"])
        }