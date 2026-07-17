import os
import json
import sys
from kafka import KafkaConsumer
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.parser import parse_log_line
from pipeline.aggregator import RollingAggregator
from pipeline.rules import check_rules
from pipeline import storage

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC  = os.getenv("KAFKA_TOPIC",  "log-events")
ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "0.7"))

# Try to load the ML model — gracefully fall back if not trained yet
try:
    from ml.inference import AnomalyDetector
    detector = AnomalyDetector()
    ML_ENABLED = True
except FileNotFoundError:
    print("⚠️  ML model not found — running rules-only mode")
    ML_ENABLED = False


def create_consumer():
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest",
        group_id="log-pipeline",
    )


def run():
    print("🔧 Initializing pipeline...")

    pg_conn = storage.get_pg_connection()
    storage.init_database(pg_conn)
    r = storage.get_redis_connection()

    aggregator = RollingAggregator(window_seconds=60)
    consumer = create_consumer()

    mode = "rules + ML" if ML_ENABLED else "rules only"
    print(f"✅ Connected to Kafka — topic: {KAFKA_TOPIC}")
    print(f"🚀 Pipeline running in [{mode}] mode. Press Ctrl+C to stop.\n")

    for message in consumer:
        raw_message = message.value
        service     = raw_message["service"]
        raw_line    = raw_message["raw"]

        # 1. PARSE
        parsed = parse_log_line(raw_line, fallback_service=service)

        # 2. STORE raw log + push to live feed
        storage.save_log(pg_conn, parsed)
        storage.push_recent_log(r, service, parsed)

        # 3. AGGREGATE
        aggregator.add(service, parsed)
        stats = aggregator.get_stats(service)
        stats["service"] = service

        # 4. RULE-BASED detection
        rule_anomaly = check_rules(service, stats)

        # 5. ML-BASED detection (runs in parallel with rules)
        ml_anomaly = None
        if ML_ENABLED:
            is_anomalous, ml_score = detector.is_anomalous(stats, ANOMALY_THRESHOLD)
            if is_anomalous:
                ml_anomaly = {
                    "rule": "ml_isolation_forest",
                    "severity": "warning" if ml_score < 0.85 else "critical",
                    "reason": f"ML anomaly score {ml_score:.2f} — unusual pattern detected",
                    "anomaly_score": ml_score,
                }

        # 6. SAVE ALERTS — rules and ML independently
        if rule_anomaly:
            storage.save_alert(pg_conn, service, rule_anomaly, stats, source="rules")
            storage.update_service_health(r, service, stats, rule_anomaly)
            print(f"🚨 [RULES] [{service}] {rule_anomaly['rule']} — {rule_anomaly['reason']}")

        if ml_anomaly:
            storage.save_alert(pg_conn, service, ml_anomaly, stats, source="ml")
            if not rule_anomaly:
                storage.update_service_health(r, service, stats, ml_anomaly)
            print(f"🤖 [ML]    [{service}] score={ml_anomaly['anomaly_score']:.2f} — {ml_anomaly['reason']}")

        if not rule_anomaly and not ml_anomaly:
            storage.update_service_health(r, service, stats, None)
            print(f"   [{service}] {parsed['level']} — "
                  f"error_rate={stats['error_rate']} logs/60s={stats['total_logs']}")


if __name__ == "__main__":
    run()