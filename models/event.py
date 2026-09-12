from extensions import db
from datetime import datetime


class Event(db.Model):
    __tablename__ = "events"

    # ── Core ──────────────────────────────────────────
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
    created_at   = db.Column(db.DateTime, default=datetime.now)
    updated_at   = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # ── Event Identity ────────────────────────────────
    event_type     = db.Column(db.String(50),  nullable=True)   # workshop / seminar / hackathon / cultural / sports / technical / other
    mode           = db.Column(db.String(20),  nullable=True)   # offline / online / hybrid
    organizer_dept = db.Column(db.String(200), nullable=True)
    speaker_name   = db.Column(db.String(200), nullable=True)
    tags           = db.Column(db.String(300), nullable=True)   # comma-separated

    # ── Media ─────────────────────────────────────────
    banner_url     = db.Column(db.String(500), nullable=True)   # S3 URL

    # ── Registration Control ──────────────────────────
    registration_deadline = db.Column(db.DateTime, nullable=True)
    has_certificate       = db.Column(db.Boolean,  default=False)
    is_paid               = db.Column(db.Boolean,  default=False)
    entry_fee             = db.Column(db.Numeric(8, 2), nullable=True)  # only if is_paid

    # ── Private (shown only after registration) ───────
    whatsapp_link  = db.Column(db.String(500), nullable=True)
    meet_link      = db.Column(db.String(500), nullable=True)
    contact_name   = db.Column(db.String(200), nullable=True)
    contact_phone  = db.Column(db.String(20),  nullable=True)
    venue_map_link = db.Column(db.String(500), nullable=True)

    # ── Relationships ─────────────────────────────────
    registrations        = db.relationship("Registration", backref="event", lazy=True)
    checkins             = db.relationship("Checkin",      backref="event", lazy=True)
    volunteer_assignment = db.relationship("VolunteerAssignment", backref="event", lazy=True)
    certificates = db.relationship("Certificate", back_populates="event", lazy=True)

    # ──────────────────────────────────────────────────
    # Completion check (no timezone math — server is IST)
    # ──────────────────────────────────────────────────
    @property
    def is_over(self):
        """True if event end datetime has passed. Pure IST — no UTC conversion."""
        event_end = datetime.combine(self.event_date, self.end_time)
        return datetime.now() > event_end

    @property
    def effective_is_completed(self):
        """Completed if admin marked it OR end time has passed."""
        return self.is_completed or self.is_over

    @property
    def hours_until_event(self):
        """Hours remaining until event starts. Negative if already started."""
        event_start = datetime.combine(self.event_date, self.start_time)
        delta = event_start - datetime.now()
        return delta.total_seconds() / 3600

    @property
    def registration_open(self):
        """False if deadline passed or event is over or completed."""
        if self.effective_is_completed:
            return False
        if self.registration_deadline and datetime.now() > self.registration_deadline:
            return False
        return True

    # ──────────────────────────────────────────────────
    # Serialization
    # ──────────────────────────────────────────────────
    def _base_dict(self):
        """Fields always safe to expose."""
        return {
            "id":                     self.id,
            "title":                  self.title,
            "description":            self.description,
            "venue":                  self.venue,
            "capacity":               self.capacity,
            "event_date":             self.event_date.isoformat(),
            "start_time":             str(self.start_time),
            "end_time":               str(self.end_time),
            "is_published":           self.is_published,
            "is_completed":           self.effective_is_completed,
            "registration_open":      self.registration_open,
            "hours_until_event":      round(self.hours_until_event, 2),
            "created_by":             self.created_by,
            "created_at":             self.created_at.isoformat(),
            "registration_count":     len([r for r in self.registrations if r.status == "registered"]),
            # ── Identity ──
            "event_type":             self.event_type,
            "mode":                   self.mode,
            "organizer_dept":         self.organizer_dept,
            "speaker_name":           self.speaker_name,
            "tags":                   self.tags,
            # ── Media ──
            "banner_url":             self.banner_url,
            # ── Registration control ──
            "registration_deadline":  self.registration_deadline.isoformat() if self.registration_deadline else None,
            "has_certificate":        self.has_certificate,
            "is_paid":                self.is_paid,
            "entry_fee":              float(self.entry_fee) if self.entry_fee else None,
        }

    def to_dict(self):
        """Public dict — no private fields. Used for admin and pre-registration views."""
        return self._base_dict()

    def to_private_dict(self):
        """Full dict — includes private fields. Used after participant registers."""
        d = self._base_dict()
        d.update({
            "whatsapp_link":  self.whatsapp_link,
            "meet_link":      self.meet_link,
            "contact_name":   self.contact_name,
            "contact_phone":  self.contact_phone,
            "venue_map_link": self.venue_map_link,
        })
        return d