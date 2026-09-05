from extensions import db
from datetime import datetime

class User(db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(150), unique=True, nullable=False)
    phone      = db.Column(db.String(15), nullable=True)
    password   = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("admin", "volunteer", "participant", name="user_role"), nullable=False, default="participant")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active  = db.Column(db.Boolean, default=True)

    # Relationships
    registrations = db.relationship("Registration", backref="user", lazy=True)
    checkins_done = db.relationship("Checkin", backref="volunteer", lazy=True)
    volunteer_assignments = db.relationship("VolunteerAssignment", backref="user", lazy=True)

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "email":      self.email,
            "phone":      self.phone,
            "role":       self.role,
            "is_active":  self.is_active,
            "created_at": self.created_at.isoformat()
        }