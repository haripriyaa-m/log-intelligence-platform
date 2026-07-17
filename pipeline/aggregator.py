import time
from collections import deque, defaultdict


class RollingAggregator:
    """
    Maintains a sliding time window of recent log events per service.

    Why a deque (double-ended queue)? Because we need to:
    1. Add new events to the right (most recent)
    2. Remove old events from the left (expired) efficiently
    A regular list would be slow for removing from the front repeatedly.

    The window_seconds defines how far back we "remember" — e.g. 60
    seconds means we always know "what happened in the last minute"
    for each service.
    """

    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        # One deque per service, storing (timestamp, parsed_log) tuples
        self.windows: dict[str, deque] = defaultdict(deque)

    def add(self, service: str, parsed_log: dict):
        """Add a new log event for a service and drop expired ones."""
        now = time.time()
        self.windows[service].append((now, parsed_log))
        self._evict_old(service, now)

    def _evict_old(self, service: str, now: float):
        """Remove events older than window_seconds from the left side."""
        window = self.windows[service]
        while window and (now - window[0][0]) > self.window_seconds:
            window.popleft()

    def get_stats(self, service: str) -> dict:
        """
        Returns current statistics for a service based on its rolling window.

        These numbers are exactly what feed into both the rule-based
        checks AND the ML model later.
        """
        now = time.time()
        self._evict_old(service, now)

        window = self.windows[service]
        total = len(window)

        if total == 0:
            return {
                "service": service,
                "total_logs": 0,
                "error_count": 0,
                "fatal_count": 0,
                "warn_count": 0,
                "error_rate": 0.0,
                "avg_severity": 0.0,
                "logs_per_second": 0.0,
            }

        error_count = sum(1 for _, log in window if log["level"] == "ERROR")
        fatal_count = sum(1 for _, log in window if log["level"] == "FATAL")
        warn_count = sum(1 for _, log in window if log["level"] == "WARN")

        severity_sum = sum(log["severity_weight"] for _, log in window)
        avg_severity = severity_sum / total

        # error_rate = fraction of logs that are ERROR or FATAL
        error_rate = (error_count + fatal_count) / total

        # How many logs per second on average across the window
        logs_per_second = total / self.window_seconds

        return {
            "service": service,
            "total_logs": total,
            "error_count": error_count,
            "fatal_count": fatal_count,
            "warn_count": warn_count,
            "error_rate": round(error_rate, 3),
            "avg_severity": round(avg_severity, 3),
            "logs_per_second": round(logs_per_second, 3),
        }

    def get_recent_logs(self, service: str, limit: int = 20) -> list[dict]:
        """Returns the most recent N logs for a service — used by the API."""
        window = self.windows[service]
        return [log for _, log in list(window)[-limit:]]