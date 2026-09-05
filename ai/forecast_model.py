"""
forecast_model.py
Defines, trains, evaluates, and persists the attendance forecast model.
"""

import os
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Path where the trained model is saved
MODEL_DIR  = os.path.join(os.path.dirname(__file__), "model_artifacts")
MODEL_PATH = os.path.join(MODEL_DIR, "forecast_model.pkl")

FEATURE_COLUMNS = [
    "capacity",
    "day_of_week",
    "month",
    "start_hour",
    "duration_hours",
    "venue_encoded",
    "registered_count",
]


def build_model() -> Pipeline:
    """Return an untrained sklearn Pipeline."""
    return Pipeline([
        ("scaler", StandardScaler()),
        ("rf", RandomForestRegressor(
            n_estimators=200,
            max_depth=10,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
        )),
    ])


def train(df: pd.DataFrame) -> dict:
    """
    Train the model on the provided DataFrame.

    Args:
        df: DataFrame with FEATURE_COLUMNS + 'checkin_count' column.

    Returns:
        dict with model, metrics, and feature importances.
    """
    X = df[FEATURE_COLUMNS]
    y = df["checkin_count"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = build_model()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae  = mean_absolute_error(y_test, y_pred)
    r2   = r2_score(y_test, y_pred)

    # Feature importances from the RF step
    importances = dict(zip(
        FEATURE_COLUMNS,
        model.named_steps["rf"].feature_importances_.tolist()
    ))

    return {
        "model":       model,
        "mae":         round(mae, 2),
        "r2":          round(r2, 4),
        "importances": importances,
        "n_train":     len(X_train),
        "n_test":      len(X_test),
    }


def save_model(model: Pipeline) -> None:
    """Persist the trained model to disk."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"[forecast_model] Model saved → {MODEL_PATH}")


def load_model() -> Pipeline:
    """Load the trained model from disk."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"No trained model found at {MODEL_PATH}. "
            "Run `python train.py` first."
        )
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    return model


def predict(model: Pipeline, features: dict) -> int:
    """
    Predict attendee count for a single event.

    Args:
        model:    Loaded sklearn Pipeline.
        features: Dict with keys matching FEATURE_COLUMNS.

    Returns:
        Predicted checkin count (integer, clamped to [0, capacity]).
    """
    row = pd.DataFrame([{col: features[col] for col in FEATURE_COLUMNS}])
    raw = model.predict(row)[0]
    capacity = features.get("capacity", raw)
    return int(np.clip(round(raw), 0, capacity))