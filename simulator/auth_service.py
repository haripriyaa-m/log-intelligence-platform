import random
from datetime import datetime

IPS = [f"192.168.{random.randint(1,255)}.{random.randint(1,255)}" for _ in range(20)]
ATTACKER_IP = "203.45.11.99"

def _timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _user_id():
    return f"u_{random.randint(1000, 9999)}"

def generate_normal_logs():
    logs = []
    user = _user_id()
    ip = random.choice(IPS)

    if random.random() < 0.85:
        logs.append(f"{_timestamp()} INFO  [auth] Login success — user: {user} — ip: {ip}")
    else:
        logs.append(f"{_timestamp()} WARN  [auth] Failed login attempt — user: {user} — ip: {ip}")
        if random.random() < 0.1:
            logs.append(f"{_timestamp()} ERROR [auth] Account locked — user: {user} — too many failed attempts")
    return logs

def generate_anomaly_brute_force():
    """ANOMALY: 10+ failed logins from same IP — brute force attack"""
    logs = []
    target_user = _user_id()
    for _ in range(random.randint(10, 20)):
        logs.append(f"{_timestamp()} WARN  [auth] Failed login attempt — user: {target_user} — ip: {ATTACKER_IP}")
    logs.append(f"{_timestamp()} ERROR [auth] Account locked — user: {target_user} — brute force detected — ip: {ATTACKER_IP}")
    return logs

def generate_anomaly_mass_lockout():
    """ANOMALY: 20+ accounts locked in 5 minutes — coordinated attack"""
    logs = []
    for _ in range(random.randint(20, 30)):
        user = _user_id()
        logs.append(f"{_timestamp()} WARN  [auth] Failed login attempt — user: {user} — ip: {ATTACKER_IP}")
        logs.append(f"{_timestamp()} ERROR [auth] Account locked — user: {user} — too many failed attempts")
    return logs