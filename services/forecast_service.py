"""
services/forecast_service.py
Wraps ai/forecast_model.py with high-level functions for routes to call.
"""

import os
from datetime import datetime
from ai.forecast_model import load_model, predict, MODEL_PATH, FEATURE_COLUMNS

# Simple venue → int encoding (must match what training used)
VENUE_MAP = {}
_venue_counter = [0]


def _encode_venue(venue: str) -> int:
    if venue not in VENUE_MAP:
        VENUE_MAP[venue] = _venue_counter[0]
        _venue_counter[0] += 1
    return VENUE_MAP[venue]


def _build_features(capacity, venue, event_date, start_time, end_time, registered_count=0):
    """Convert raw event fields into the feature dict the model expects."""

    # Parse date
    if isinstance(event_date, str):
        event_date = datetime.strptime(event_date, "%Y-%m-%d").date()

    # Parse times
    if isinstance(start_time, str):
        start_time = datetime.strptime(start_time, "%H:%M:%S").time()
    if isinstance(end_time, str):
        end_time = datetime.strptime(end_time, "%H:%M:%S").time()

    duration_hours = (
        datetime.combine(event_date, end_time) -
        datetime.combine(event_date, start_time)
    ).seconds / 3600

    return {
        "capacity":        int(capacity),
        "day_of_week":     event_date.weekday(),        # 0=Mon … 6=Sun
        "month":           event_date.month,
        "start_hour":      start_time.hour,
        "duration_hours":  duration_hours,
        "venue_encoded":   _encode_venue(str(venue)),
        "registered_count": int(registered_count or 0),
    }


def predict_attendance(event) -> dict:
    """
    Predict attendance for a saved Event model instance.
    Raises FileNotFoundError if the model hasn't been trained yet.
    """
    model    = load_model()
    features = _build_features(
        capacity         = event.capacity,
        venue            = event.venue,
        event_date       = event.event_date,
        start_time       = event.start_time,
        end_time         = event.end_time,
        registered_count = len([r for r in event.registrations if r.status == "registered"])
                           if event.registrations else 0,
    )
    predicted = predict(model, features)
    return {
        "predicted_attendance": predicted,
        "capacity":             event.capacity,
        "utilization_pct":      round(predicted / event.capacity * 100, 1) if event.capacity else 0,
        "features_used":        features,
    }


def predict_attendance_from_dict(data: dict) -> dict:
    """
    Predict attendance from raw dict (used by forecast/preview endpoint).
    Raises FileNotFoundError if the model hasn't been trained yet.
    """
    model    = load_model()
    features = _build_features(
        capacity         = data["capacity"],
        venue            = data.get("venue", "unknown"),
        event_date       = data["event_date"],
        start_time       = data["start_time"],
        end_time         = data["end_time"],
        registered_count = data.get("registered_count", 0),
    )
    predicted = predict(model, features)
    capacity  = int(data["capacity"])
    return {
        "predicted_attendance": predicted,
        "capacity":             capacity,
        "utilization_pct":      round(predicted / capacity * 100, 1) if capacity else 0,
        "features_used":        features,
    }


def get_model_status() -> dict:
    """Return whether the model file exists and basic metadata."""
    exists = os.path.exists(MODEL_PATH)
    result = {
        "model_trained": exists,
        "model_path":    MODEL_PATH,
    }
    if exists:
        result["model_size_kb"] = round(os.path.getsize(MODEL_PATH) / 1024, 1)
        result["last_modified"] = datetime.fromtimestamp(
            os.path.getmtime(MODEL_PATH)
        ).isoformat()
    return result