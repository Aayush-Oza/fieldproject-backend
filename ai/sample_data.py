"""
sample_data.py
Generates synthetic event attendance data for training the forecast model.
"""

import pandas as pd
import numpy as np
import random
from datetime import date, timedelta

random.seed(42)
np.random.seed(42)

VENUES = ["Main Hall", "Auditorium", "Conference Room", "Open Ground", "Lab"]
DAYS_OF_WEEK = list(range(7))  # 0=Monday, 6=Sunday


def generate_sample_data(n_samples: int = 500) -> pd.DataFrame:
    """
    Generate synthetic training data mimicking real event patterns.

    Features:
        - capacity         : max seats available
        - day_of_week      : 0=Mon … 6=Sun
        - month            : 1–12
        - start_hour       : hour the event starts (0–23)
        - duration_hours   : length of event in hours
        - venue_encoded    : integer-encoded venue
        - registered_count : number of people who registered  (input feature)

    Target:
        - checkin_count    : actual attendees (what we predict)
    """

    records = []
    venue_map = {v: i for i, v in enumerate(VENUES)}

    base_date = date.today() - timedelta(days=365)

    for _ in range(n_samples):
        capacity = random.choice([50, 100, 150, 200, 300, 500])
        venue = random.choice(VENUES)
        day_of_week = random.randint(0, 6)
        month = random.randint(1, 12)
        start_hour = random.choice([9, 10, 11, 14, 15, 16, 18])
        duration_hours = random.choice([1, 2, 3, 4, 6])

        # Simulate realistic registration rate (60–95% of capacity)
        reg_rate = random.uniform(0.6, 0.95)
        registered_count = int(capacity * reg_rate)

        # Simulate show-up rate influenced by factors
        base_show_rate = 0.75

        # Weekends slightly lower turnout
        if day_of_week >= 5:
            base_show_rate -= 0.05

        # Morning/evening slots slightly higher
        if start_hour in [9, 10, 18]:
            base_show_rate += 0.05

        # Summer months slightly lower
        if month in [5, 6, 7]:
            base_show_rate -= 0.03

        # Add noise
        show_rate = np.clip(base_show_rate + np.random.normal(0, 0.07), 0.3, 1.0)
        checkin_count = int(registered_count * show_rate)

        records.append({
            "capacity":         capacity,
            "day_of_week":      day_of_week,
            "month":            month,
            "start_hour":       start_hour,
            "duration_hours":   duration_hours,
            "venue_encoded":    venue_map[venue],
            "registered_count": registered_count,
            "checkin_count":    checkin_count,
        })

    df = pd.DataFrame(records)
    return df


VENUE_MAP = {v: i for i, v in enumerate(VENUES)}


def encode_venue(venue_name: str) -> int:
    """Return integer encoding for a venue name (unknown venues → 0)."""
    return VENUE_MAP.get(venue_name, 0)


if __name__ == "__main__":
    df = generate_sample_data()
    print(df.head(10))
    print(f"\nGenerated {len(df)} samples")
    print(df.describe())