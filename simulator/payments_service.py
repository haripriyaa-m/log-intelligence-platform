import random
import time
from datetime import datetime


# These are realistic transaction amounts for an e-commerce platform
TRANSACTION_AMOUNTS = [149, 299, 499, 999, 1499, 2999, 4999, 9999]

# Payment gateways your platform uses
GATEWAYS = ["razorpay", "stripe", "paytm"]


def _timestamp():
    """Returns current time in standard log format"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _transaction_id():
    """Generates a realistic transaction ID"""
    return f"txn_{random.randint(10000, 99999)}"


def _user_id():
    """Generates a realistic user ID"""
    return f"u_{random.randint(1000, 9999)}"


def generate_normal_logs():
    """
    Generates a batch of normal payments logs.
    Most of the time, payments succeed. Occasionally a single timeout happens.
    This represents healthy system behaviour.
    """
    logs = []
    txn_id = _transaction_id()
    user = _user_id()
    amount = random.choice(TRANSACTION_AMOUNTS)
    gateway = random.choice(GATEWAYS)

    # 90% of the time: clean successful transaction
    if random.random() < 0.90:
        logs.append(
            f"{_timestamp()} INFO  [payments] Transaction {txn_id} initiated "
            f"— amount: ₹{amount} user: {user} gateway: {gateway}"
        )
        time.sleep(random.uniform(0.1, 0.3))  # simulate processing time
        logs.append(
            f"{_timestamp()} INFO  [payments] Payment gateway response: SUCCESS "
            f"— {txn_id} — gateway: {gateway}"
        )

    # 10% of the time: a single timeout (normal, not an anomaly)
    else:
        logs.append(
            f"{_timestamp()} INFO  [payments] Transaction {txn_id} initiated "
            f"— amount: ₹{amount} user: {user} gateway: {gateway}"
        )
        logs.append(
            f"{_timestamp()} WARN  [payments] Gateway slow response "
            f"— {txn_id} — elapsed: {random.randint(800, 1200)}ms"
        )
        logs.append(
            f"{_timestamp()} ERROR [payments] Payment gateway timeout "
            f"— {txn_id} — retry 1/3"
        )
        logs.append(
            f"{_timestamp()} INFO  [payments] Payment gateway response: SUCCESS "
            f"— {txn_id} — retry succeeded"
        )

    return logs


def generate_anomaly_gateway_failure():
    """
    ANOMALY: Gateway cascade failure.
    3+ consecutive transactions timing out and failing completely.
    This indicates the payment gateway is down — a critical production incident.
    """
    logs = []
    gateway = random.choice(GATEWAYS)

    for _ in range(random.randint(4, 7)):
        txn_id = _transaction_id()
        user = _user_id()
        amount = random.choice(TRANSACTION_AMOUNTS)

        logs.append(
            f"{_timestamp()} INFO  [payments] Transaction {txn_id} initiated "
            f"— amount: ₹{amount} user: {user} gateway: {gateway}"
        )
        logs.append(
            f"{_timestamp()} ERROR [payments] Payment gateway timeout "
            f"— {txn_id} — retry 1/3"
        )
        logs.append(
            f"{_timestamp()} ERROR [payments] Payment gateway timeout "
            f"— {txn_id} — retry 2/3"
        )
        logs.append(
            f"{_timestamp()} ERROR [payments] Payment gateway timeout "
            f"— {txn_id} — retry 3/3"
        )
        logs.append(
            f"{_timestamp()} FATAL [payments] Transaction failed "
            f"— {txn_id} — max retries exceeded — gateway: {gateway}"
        )

    return logs


def generate_anomaly_volume_spike():
    """
    ANOMALY: Sudden transaction volume spike.
    10x normal volume in a short time — could be a bot attack or
    a flash sale causing system strain.
    """
    logs = []

    for _ in range(random.randint(15, 25)):
        txn_id = _transaction_id()
        user = _user_id()
        amount = random.choice(TRANSACTION_AMOUNTS)
        gateway = random.choice(GATEWAYS)

        logs.append(
            f"{_timestamp()} INFO  [payments] Transaction {txn_id} initiated "
            f"— amount: ₹{amount} user: {user} gateway: {gateway}"
        )
        # During spike, success rate drops due to overload
        if random.random() < 0.6:
            logs.append(
                f"{_timestamp()} INFO  [payments] Payment gateway response: SUCCESS "
                f"— {txn_id}"
            )
        else:
            logs.append(
                f"{_timestamp()} ERROR [payments] Payment gateway timeout "
                f"— {txn_id} — system overloaded"
            )

    return logs