"""
Loads model.onnx and runs real-time inference on live aggregator stats.

This runs inside the pipeline consumer — for every log message processed,
we call score() with the current service stats and get back an anomaly score.

Key property: the ONNX Runtime loads the model ONCE at startup and keeps
it in memory. Each call to score() is just a matrix multiply — microseconds.
"""

import json
import os
import numpy as np
import onnxruntime as rt


FEATURES = [
    "total_logs",
    "error_count",
    "fatal_count",
    "warn_count",
    "error_rate",
    "avg_severity",
    "logs_per_second",
]

MODEL_PATH = "ml/model.onnx"


class AnomalyDetector:
    """
    Wraps the ONNX Runtime session for clean inference.
    Instantiate once, call score() many times.
    """

    def __init__(self, model_path: str = MODEL_PATH):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
                "Run ml/train_model.py first."
            )

        # Load the ONNX model into the runtime session
        # This is the expensive step — happens once at startup
        self.session = rt.InferenceSession(model_path)

        # Get input/output names from the model
        self.input_name = self.session.get_inputs()[0].name
        self.output_label = self.session.get_outputs()[0].name
        self.output_score = self.session.get_outputs()[1].name

        # Track per-service score history for normalisation
        self._score_history: dict[str, list] = {}

        print(f"✅ ONNX model loaded from {model_path}")

    def score(self, stats: dict) -> float:
        """
        Takes aggregator stats dict and returns anomaly score 0.0-1.0.

        0.0 = perfectly normal
        1.0 = highly anomalous

        Returns 0.0 if total_logs < 5 — not enough data to judge yet.
        """
        if stats.get("total_logs", 0) < 5:
            return 0.0

        # Build the feature vector in the exact same order as training
        features = np.array(
            [[stats.get(f, 0.0) for f in FEATURES]],
            dtype=np.float32
        )

        # Run inference
        outputs = self.session.run(
            [self.output_label, self.output_score],
            {self.input_name: features}
        )

        # outputs[0] is the label: -1 (anomaly) or 1 (normal)
        # outputs[1] is a numpy array of shape (1, 2) with raw probabilities
        label = outputs[0][0]
        raw_score = float(outputs[1][0])

        # raw_score is the decision function value:
        # positive = normal, negative = anomalous
        # We convert to 0-1 where 1 = most anomalous
        # Scores typically range from -0.2 to +0.2
        # Formula: anomalous when raw < 0, scale to 0-1
        if raw_score >= 0:
            anomaly_score = 0.0
        else:
            # Scale negative scores: -0.05 → ~0.5, -0.17 → ~1.0
            anomaly_score = float(np.clip(abs(raw_score) / 0.17, 0.0, 1.0))

        # Track history for this service
        service = stats.get("service", "unknown")
        if service not in self._score_history:
            self._score_history[service] = []
        self._score_history[service].append(anomaly_score)

        return anomaly_score

    def is_anomalous(self, stats: dict, threshold: float = 0.7) -> tuple[bool, float]:
        """
        Convenience method — returns (is_anomalous, score).
        threshold=0.7 means "flag if 70%+ anomalous probability".
        """
        score = self.score(stats)
        return score >= threshold, score