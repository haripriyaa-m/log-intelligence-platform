import os
import json
import psycopg2
import redis
from dotenv import load_dotenv

load_dotenv()

PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")
PG_USER = os.getenv("POSTGRES_USER", "loguser")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "logpass")
PG_DB = os.getenv("POSTGRES_DB", "logdb")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))


def get_pg_connection():
    """
    Creates a PostgreSQL connection.
    autocommit=True means each query commits immediately —
    fine for our use case since we're doing simple inserts,
    not multi-step transactions.
    """
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        user=PG_USER, password=PG_PASSWORD, dbname=PG_DB,
    )
    conn.autocommit = True
    return conn


def get_redis_connection():
    import os
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return redis.from_url(redis_url, decode_responses=True)
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
    )

def init_database(conn):
    """
    Creates the tables we need if they don't exist yet.
    Runs once when the pipeline starts.

    Two tables:
    - logs: every parsed log line, permanently
    - alerts: every anomaly that was detected
    """
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                service VARCHAR(50) NOT NULL,
                level VARCHAR(10) NOT NULL,
                severity_weight INT NOT NULL,
                message TEXT NOT NULL,
                transaction_id VARCHAR(50),
                user_id VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                service VARCHAR(50) NOT NULL,
                rule VARCHAR(100),
                severity VARCHAR(20) NOT NULL,
                reason TEXT NOT NULL,
                source VARCHAR(20) NOT NULL,
                anomaly_score FLOAT,
                stats JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # Indexes speed up the queries our API will run later
        cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_service ON logs(service);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_service ON alerts(service);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);")

    print("✅ Database tables ready")


def save_log(conn, parsed_log: dict):
    """Inserts one parsed log line into PostgreSQL."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO logs (timestamp, service, level, severity_weight,
                               message, transaction_id, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            parsed_log["timestamp"], parsed_log["service"], parsed_log["level"],
            parsed_log["severity_weight"], parsed_log["message"],
            parsed_log["transaction_id"], parsed_log["user_id"],
        ))


def save_alert(conn, service: str, anomaly: dict, stats: dict, source: str):
    """
    Inserts a detected anomaly into the alerts table.

    source distinguishes whether this alert came from "rules" or "ml" —
    important for your demo, so you can show both detection paths working.
    """
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO alerts (service, rule, severity, reason, source,
                                 anomaly_score, stats)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            service,
            anomaly.get("rule"),
            anomaly.get("severity", "warning"),
            anomaly.get("reason", ""),
            source,
            anomaly.get("anomaly_score"),
            json.dumps(stats),
        ))


def update_service_health(r: redis.Redis, service: str, stats: dict, anomaly: dict | None):
    """
    Updates Redis with the CURRENT state of a service.

    This is what the dashboard and API read for live data — it's a
    single key per service that always holds the latest snapshot.
    Much faster than querying PostgreSQL on every dashboard refresh.
    """
    health_status = "healthy"
    if anomaly:
        health_status = anomaly.get("severity", "warning")

    state = {
        "service": service,
        "status": health_status,
        "stats": stats,
        "active_anomaly": anomaly,
    }

    r.set(f"health:{service}", json.dumps(state))
    # Also keep a list of all known services for easy lookup
    r.sadd("known_services", service)


def push_recent_log(r: redis.Redis, service: str, parsed_log: dict, max_items: int = 50):
    """
    Pushes a log line onto a Redis list for live feed display.
    Keeps only the most recent max_items — older ones get trimmed.
    """
    key = f"recent_logs:{service}"
    r.lpush(key, json.dumps(parsed_log))
    r.ltrim(key, 0, max_items - 1)
