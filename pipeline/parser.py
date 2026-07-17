import re
from datetime import datetime


# Matches lines like:
# 2024-01-15 14:23:08 ERROR [payments] Payment gateway timeout — txn_8829 — retry 2/3
LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+"
    r"(?P<level>INFO|WARN|ERROR|FATAL)\s+"
    r"\[(?P<service>\w+)\]\s+"
    r"(?P<message>.*)$"
)

# Extracts transaction IDs like txn_8829
TXN_PATTERN = re.compile(r"txn_(\d+)")

# Extracts user IDs like u_4521
USER_PATTERN = re.compile(r"u_(\d+)")

# Severity levels mapped to numeric weight.
# Higher weight = more severe. Used later for anomaly scoring.
SEVERITY_WEIGHT = {
    "INFO": 0,
    "WARN": 1,
    "ERROR": 2,
    "FATAL": 3,
}


def parse_log_line(raw_line: str, fallback_service: str) -> dict:
    """
    Takes a raw log string and returns a structured dictionary.

    If the line doesn't match the expected format (shouldn't happen with
    our simulator, but real-world logs are messy), we fall back gracefully
    instead of crashing the whole pipeline.
    """
    match = LOG_PATTERN.match(raw_line)

    if not match:
        # Fallback for unparseable lines — still store them, just with
        # less structure. Real production systems see malformed logs
        # constantly, so this safety net matters.
        return {
            "timestamp": datetime.now().isoformat(),
            "service": fallback_service,
            "level": "UNKNOWN",
            "severity_weight": 0,
            "message": raw_line,
            "transaction_id": None,
            "user_id": None,
        }

    fields = match.groupdict()
    message = fields["message"]

    # Try to pull out useful structured fields from the message text
    txn_match = TXN_PATTERN.search(message)
    user_match = USER_PATTERN.search(message)

    return {
        "timestamp": fields["timestamp"],
        "service": fields["service"],
        "level": fields["level"],
        "severity_weight": SEVERITY_WEIGHT.get(fields["level"], 0),
        "message": message,
        "transaction_id": f"txn_{txn_match.group(1)}" if txn_match else None,
        "user_id": f"u_{user_match.group(1)}" if user_match else None,
    }