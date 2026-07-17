"""
Scenarios — inject anomalies manually to test detection.

Run this in a second terminal while producer.py is running:
    python simulator/scenarios.py --scenario gateway_failure
    python simulator/scenarios.py --scenario brute_force
    python simulator/scenarios.py --scenario db_deadlock
    python simulator/scenarios.py --scenario api_cascade
    python simulator/scenarios.py --scenario all
"""

import argparse
import json
import os
import time
from datetime import datetime
from kafka import KafkaProducer
from dotenv import load_dotenv

load_dotenv()

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC  = os.getenv("KAFKA_TOPIC",  "log-events")

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator import payments_service, auth_service, database_service, api_gateway


def get_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",
    )


def inject(producer, logs, service_name, scenario_name):
    print(f"\n🚨 INJECTING: {scenario_name} on [{service_name}] — {len(logs)} log lines")
    for log_line in logs:
        message = {
            "raw": log_line,
            "service": service_name,
            "ingested_at": datetime.now().isoformat(),
            "injected_scenario": scenario_name,
        }
        producer.send(KAFKA_TOPIC, value=message)
    producer.flush()
    print(f"✅ Injection complete\n")


def main():
    parser = argparse.ArgumentParser(description="Inject anomaly scenarios")
    parser.add_argument("--scenario", required=True,
        choices=["gateway_failure", "brute_force", "mass_lockout",
                 "db_pool", "db_deadlock", "api_cascade", "latency_creep", "all"],
        help="Which anomaly scenario to inject"
    )
    args = parser.parse_args()

    producer = get_producer()

    scenarios = {
        "gateway_failure": (payments_service.generate_anomaly_gateway_failure,  "payments"),
        "brute_force":     (auth_service.generate_anomaly_brute_force,          "auth"),
        "mass_lockout":    (auth_service.generate_anomaly_mass_lockout,          "auth"),
        "db_pool":         (database_service.generate_anomaly_connection_pool,   "database"),
        "db_deadlock":     (database_service.generate_anomaly_deadlock,          "database"),
        "api_cascade":     (api_gateway.generate_anomaly_503_cascade,            "api_gateway"),
        "latency_creep":   (api_gateway.generate_anomaly_latency_creep,          "api_gateway"),
    }

    if args.scenario == "all":
        for name, (fn, svc) in scenarios.items():
            inject(producer, fn(), svc, name)
            time.sleep(1)
    else:
        fn, svc = scenarios[args.scenario]
        inject(producer, fn(), svc, args.scenario)


if __name__ == "__main__":
    main()