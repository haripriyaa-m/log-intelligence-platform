import time
import json
import random
import os
from datetime import datetime
from kafka import KafkaProducer
from dotenv import load_dotenv

# Load config from .env file
load_dotenv()

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "log-events")
LOG_INTERVAL = float(os.getenv("LOG_INTERVAL_SECONDS", "0.5"))

# Import all four service simulators
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator import payments_service, auth_service, database_service, api_gateway


def create_producer():
    """
    Creates a Kafka producer.
    Retries every 2 seconds if Kafka isn't ready yet.
    This handles the case where Kafka takes a moment to start.
    """
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                # Serialise each message as JSON bytes
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                # Wait for Kafka to confirm receipt
                acks="all",
            )
            print(f"✅ Connected to Kafka at {KAFKA_BROKER}")
            return producer
        except Exception as e:
            print(f"⏳ Waiting for Kafka... ({e})")
            time.sleep(2)


def publish_logs(producer, logs, service_name):
    """
    Takes a list of raw log strings and publishes each one
    to Kafka as a structured JSON message.
    
    We add metadata here — source service and ingest timestamp —
    so the pipeline knows where each log came from.
    """
    for log_line in logs:
        message = {
            "raw": log_line,
            "service": service_name,
            "ingested_at": datetime.now().isoformat(),
        }
        producer.send(KAFKA_TOPIC, value=message)
    
    # Flush ensures messages are actually sent, not just buffered
    producer.flush()


def run():
    """
    Main loop. Runs forever, generating logs from all four services
    and publishing them to Kafka continuously.
    """
    producer = create_producer()
    
    # Map each service name to its normal log generator
    services = {
        "payments":    payments_service.generate_normal_logs,
        "auth":        auth_service.generate_normal_logs,
        "database":    database_service.generate_normal_logs,
        "api_gateway": api_gateway.generate_normal_logs,
    }

    print(f"🚀 Log simulator running — publishing to topic: {KAFKA_TOPIC}")
    print("   Press Ctrl+C to stop\n")

    cycle = 0
    while True:
        # Each cycle, randomly pick 1-3 services to generate logs
        # This mimics real systems where not all services are equally busy
        active_services = random.sample(list(services.items()), k=random.randint(1, 3))
        
        for service_name, generator in active_services:
            logs = generator()
            publish_logs(producer, logs, service_name)
            print(f"  📤 {service_name}: {len(logs)} log(s) published")

        cycle += 1
        
        # Every 30 cycles, print a summary
        if cycle % 30 == 0:
            print(f"\n--- {cycle} cycles completed ---\n")

        time.sleep(LOG_INTERVAL)


if __name__ == "__main__":
    run()