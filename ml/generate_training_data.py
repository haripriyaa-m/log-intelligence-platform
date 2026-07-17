"""
Generates synthetic NORMAL log statistics for training the Isolation Forest.

We don't train on raw log lines — we train on the same rolling window
STATISTICS that the aggregator computes in real time. This means the model
learns "what do healthy stats look like?" rather than "what do healthy
log strings look like?"

This is an important design decision: the model's input at training time
is identical to its input at inference time — the feature vector from
the aggregator. No mismatch between training and production.
"""

import pandas as pd
import numpy as np
import os

# Reproducible results
np.random.seed(42)

# How many normal samples to generate per service
SAMPLES_PER_SERVICE = 2000


def generate_payments_normal(n):
    """
    Normal payments service stats:
    - Low error rate (0–15%)
    - Moderate log volume
    - Rarely any fatal events
    """
    return pd.DataFrame({
        "service":         ["payments"] * n,
        "total_logs":      np.random.randint(5, 40, n),
        "error_count":     np.random.randint(0, 4, n),
        "fatal_count":     np.random.choice([0, 1], n, p=[0.97, 0.03]),
        "warn_count":      np.random.randint(0, 6, n),
        "error_rate":      np.random.uniform(0.0, 0.15, n),
        "avg_severity":    np.random.uniform(0.0, 0.4, n),
        "logs_per_second": np.random.uniform(0.05, 0.6, n),
    })


def generate_auth_normal(n):
    """
    Normal auth service stats:
    - Very low error rate (0–10%)
    - Low warn count (occasional failed logins are normal)
    - No fatals under normal conditions
    """
    return pd.DataFrame({
        "service":         ["auth"] * n,
        "total_logs":      np.random.randint(3, 25, n),
        "error_count":     np.random.randint(0, 2, n),
        "fatal_count":     np.zeros(n, dtype=int),
        "warn_count":      np.random.randint(0, 4, n),
        "error_rate":      np.random.uniform(0.0, 0.10, n),
        "avg_severity":    np.random.uniform(0.0, 0.3, n),
        "logs_per_second": np.random.uniform(0.03, 0.4, n),
    })


def generate_database_normal(n):
    """
    Normal database stats:
    - Mostly INFO logs with occasional WARN (slow queries)
    - warn_count up to 7 is normal (30% of queries can be slow)
    - No fatals, very few errors
    """
    return pd.DataFrame({
        "service":         ["database"] * n,
        "total_logs":      np.random.randint(4, 30, n),
        "error_count":     np.random.randint(0, 2, n),
        "fatal_count":     np.zeros(n, dtype=int),
        "warn_count":      np.random.randint(0, 7, n),
        "error_rate":      np.random.uniform(0.0, 0.08, n),
        "avg_severity":    np.random.uniform(0.0, 0.35, n),
        "logs_per_second": np.random.uniform(0.04, 0.5, n),
    })


def generate_api_gateway_normal(n):
    """
    Normal API gateway stats:
    - Very low error rate (mostly 200s)
    - Higher log volume than other services (all traffic goes through it)
    - Occasional warn for latency spikes
    """
    return pd.DataFrame({
        "service":         ["api_gateway"] * n,
        "total_logs":      np.random.randint(8, 50, n),
        "error_count":     np.random.randint(0, 3, n),
        "fatal_count":     np.zeros(n, dtype=int),
        "warn_count":      np.random.randint(0, 4, n),
        "error_rate":      np.random.uniform(0.0, 0.08, n),
        "avg_severity":    np.random.uniform(0.0, 0.25, n),
        "logs_per_second": np.random.uniform(0.1, 0.8, n),
    })


def main():
    print("Generating normal training data...")

    dfs = [
        generate_payments_normal(SAMPLES_PER_SERVICE),
        generate_auth_normal(SAMPLES_PER_SERVICE),
        generate_database_normal(SAMPLES_PER_SERVICE),
        generate_api_gateway_normal(SAMPLES_PER_SERVICE),
    ]

    df = pd.concat(dfs, ignore_index=True)

    # Shuffle so services are mixed (not all payments first, then all auth etc.)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    os.makedirs("ml", exist_ok=True)
    output_path = "ml/training_data.csv"
    df.to_csv(output_path, index=False)

    print(f"✅ Generated {len(df)} normal samples across 4 services")
    print(f"   Saved to {output_path}")
    print(f"\nSample preview:")
    print(df.head(8).to_string(index=False))


if __name__ == "__main__":
    main()
