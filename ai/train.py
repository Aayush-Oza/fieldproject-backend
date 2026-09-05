"""
train.py
Run this script once to train and save the forecast model.

Usage:
    cd backend
    python -m ai.train
        OR
    python ai/train.py
"""

import sys
import os

# Allow running from backend/ or backend/ai/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai.sample_data import generate_sample_data
from ai.forecast_model import train, save_model


def main():
    print("=" * 50)
    print("  Attendance Forecast Model - Training")
    print("=" * 50)

    print("\n[1/3] Generating synthetic training data...")
    df = generate_sample_data(n_samples=1000)
    print(f"      Generated {len(df)} records.")

    print("\n[2/3] Training Random Forest model...")
    result = train(df)

    print(f"\n      ✅ Training complete!")
    print(f"      Train samples : {result['n_train']}")
    print(f"      Test  samples : {result['n_test']}")
    print(f"      MAE           : {result['mae']} attendees")
    print(f"      R² Score      : {result['r2']}")

    print("\n      Feature importances:")
    for feat, imp in sorted(result["importances"].items(), key=lambda x: -x[1]):
        bar = "█" * int(imp * 40)
        print(f"        {feat:<20} {bar} {imp:.4f}")

    print("\n[3/3] Saving model to disk...")
    save_model(result["model"])

    print("\n✅ Done! Model is ready for forecast_service.py\n")


if __name__ == "__main__":
    main()