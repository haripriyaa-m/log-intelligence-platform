"""
Trains an Isolation Forest on normal log statistics and exports to ONNX.

Why Isolation Forest?
- Unsupervised: no labelled anomaly data needed
- Works by randomly partitioning the feature space — anomalies
  are isolated in fewer splits than normal points
- Fast to train, fast to predict, small model size
- Proven in production monitoring systems

Why ONNX export?
- Decouples training (Python/scikit-learn) from inference (any runtime)
- The pipeline loads model.onnx once at startup and runs it in-process
- No Python ML dependencies needed at inference time
- Same model file could run in Java, C++, or .NET if needed later
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import pickle
import os

# skl2onnx converts scikit-learn pipelines to ONNX format
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType


# These are the exact features the aggregator computes in real time.
# The order here MUST match the order we feed features during inference.
FEATURES = [
    "total_logs",
    "error_count",
    "fatal_count",
    "warn_count",
    "error_rate",
    "avg_severity",
    "logs_per_second",
]


def load_training_data():
    path = "ml/training_data.csv"
    if not os.path.exists(path):
        raise FileNotFoundError(
            "Training data not found. Run generate_training_data.py first."
        )
    df = pd.read_csv(path)
    print(f"✅ Loaded {len(df)} training samples")
    return df[FEATURES].values.astype(np.float32)


def train(X):
    """
    Build a Pipeline with two steps:
    1. StandardScaler — normalises each feature to mean=0, std=1
       This prevents features with large ranges (total_logs: 0-50)
       from dominating features with small ranges (error_rate: 0-1)
    2. IsolationForest — the anomaly detector

    Key hyperparameters:
    - contamination=0.05: we tell the model to expect ~5% anomalies
      in any real stream. This sets the decision threshold internally.
    - n_estimators=100: number of isolation trees. More = more stable
      but diminishing returns beyond ~200.
    - random_state=42: reproducible results
    """
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", IsolationForest(
            contamination=0.05,
            n_estimators=100,
            random_state=42,
        ))
    ])

    print("Training Isolation Forest...")
    pipeline.fit(X)
    print("✅ Training complete")
    return pipeline


def export_onnx(pipeline, output_path="ml/model.onnx"):
    """
    Converts the trained scikit-learn pipeline to ONNX format.

    initial_type tells the converter what shape the input will be:
    - FloatTensorType([None, 7]) means:
      - None rows (batch size is flexible)
      - 7 columns (one per feature)
    """
    n_features = len(FEATURES)
    initial_type = [("float_input", FloatTensorType([None, n_features]))]

    onnx_model = convert_sklearn(
        pipeline,
        initial_types=initial_type,
        target_opset={"": 12, "ai.onnx.ml": 3},
    )

    with open(output_path, "wb") as f:
        f.write(onnx_model.SerializeToString())

    size_kb = os.path.getsize(output_path) / 1024
    print(f"✅ ONNX model exported to {output_path} ({size_kb:.1f} KB)")


def save_metadata():
    """
    Save the feature list alongside the model.
    This ensures inference code always uses the right feature order.
    """
    import json
    meta = {"features": FEATURES, "n_features": len(FEATURES)}
    with open("ml/model_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"✅ Model metadata saved to ml/model_metadata.json")


def quick_test(pipeline, X):
    """
    Sanity check: score the training data itself.
    Most samples should score as normal (-1 = anomaly, 1 = normal in sklearn).
    We convert to a 0-1 anomaly score for easier reading.
    """
    scores = pipeline.decision_function(X)
    # decision_function returns higher = more normal
    # We invert and normalise to 0-1 where 1 = most anomalous
    anomaly_scores = 1 - (scores - scores.min()) / (scores.max() - scores.min())

    pct_flagged = (anomaly_scores > 0.7).mean() * 100
    print(f"\nSanity check on training data:")
    print(f"   Mean anomaly score: {anomaly_scores.mean():.3f}")
    print(f"   % flagged as anomalous (>0.7): {pct_flagged:.1f}%")
    print(f"   (Should be ~5% since contamination=0.05)")


def main():
    print("=" * 50)
    print("Week 3: Training Isolation Forest")
    print("=" * 50)

    X = load_training_data()
    pipeline = train(X)
    quick_test(pipeline, X)
    export_onnx(pipeline)
    save_metadata()

    print("\n✅ All done. model.onnx is ready for the pipeline.")


if __name__ == "__main__":
    main()