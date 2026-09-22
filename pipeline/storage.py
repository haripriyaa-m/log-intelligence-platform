import os
import json
import psycopg2
import redis
from dotenv import load_dotenv

load_dotenv()

PG_HOST     = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT     = os.getenv("POSTGRES_PORT", "5432")
PG_USER     = os.getenv("POSTGRES_USER", "loguser")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "logpass")
PG_DB       = os.getenv("POSTGRES_DB", "logdb")
REDIS_HOST  = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT  = int(os.getenv("REDIS_PORT", "6379"))


def get_pg_connection():
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        user=PG_USER, password=PG_PASSWORD, dbname=PG_DB,
    )
    conn.autocommit = True
    return conn


def get_redis_connection():
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return redis.from_url(redis_url, decode_responses=True)
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def init_database():
    conn = get_pg_connection()
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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_service ON logs(service);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_service ON alerts(service);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);")
    conn.close()
    print("✅ Database tables ready")


def save_log(parsed_log: dict):
    conn = get_pg_connection()
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
    conn.close()


def save_alert(service: str, anomaly: dict, stats: dict, source: str):
    conn = get_pg_connection()
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
    conn.close()


def update_service_health(r, service: str, stats: dict, anomaly: dict | None):
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
    r.sadd("known_services", service)


def push_recent_log(r, service: str, parsed_log: dict, max_items: int = 50):
    key = f"recent_logs:{service}"
    r.lpush(key, json.dumps(parsed_log))
    r.ltrim(key, 0, max_items - 1)