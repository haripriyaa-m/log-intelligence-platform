import random
from datetime import datetime

QUERIES = [
    "SELECT orders WHERE user_id={}",
    "SELECT * FROM transactions LIMIT 100",
    "INSERT INTO sessions VALUES ({})",
    "UPDATE users SET last_login=NOW() WHERE id={}",
]

def _timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def generate_normal_logs():
    logs = []
    query = random.choice(QUERIES).format(random.randint(1000, 9999))
    latency = random.randint(5, 50)

    if latency > 30:
        logs.append(f"{_timestamp()} WARN  [database] Slow query detected — {latency}ms — {query}")
    else:
        logs.append(f"{_timestamp()} INFO  [database] Query executed — {latency}ms — {query}")
    return logs

def generate_anomaly_connection_pool():
    """ANOMALY: Connection pool exhausted — all 100 connections in use"""
    logs = []
    for _ in range(random.randint(5, 10)):
        logs.append(f"{_timestamp()} ERROR [database] Connection pool exhausted — active: 100/100")
    logs.append(f"{_timestamp()} FATAL [database] Unable to acquire connection — requests queuing")
    return logs

def generate_anomaly_deadlock():
    """ANOMALY: Multiple deadlocks in quick succession"""
    logs = []
    for _ in range(random.randint(3, 6)):
        logs.append(f"{_timestamp()} ERROR [database] Deadlock detected — rolling back transaction")
        logs.append(f"{_timestamp()} WARN  [database] Transaction retry after deadlock — attempt {random.randint(1,3)}/3")
    logs.append(f"{_timestamp()} FATAL [database] Deadlock cascade — {random.randint(3,6)} transactions failed")
    return logs