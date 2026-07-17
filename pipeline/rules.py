"""
Rule-based anomaly detection.

These are hardcoded thresholds based on domain knowledge — "if X happens,
it's definitely a problem, regardless of what the ML model thinks."

Real production systems (Datadog, Splunk) all have a rules layer like
this. It catches KNOWN failure patterns instantly and explainably.
The ML model (Week 3) catches UNKNOWN patterns the rules don't cover.

Each rule function takes the current rolling stats for a service and
returns either None (no anomaly) or a dict describing the anomaly.
"""


def check_payments_rules(stats: dict) -> dict | None:
    if stats["total_logs"] < 3:
        return None  # not enough data yet to judge

    if stats["fatal_count"] >= 3:
        return {
            "rule": "gateway_cascade_failure",
            "severity": "critical",
            "reason": f"{stats['fatal_count']} fatal payment failures in last 60s",
        }

    if stats["error_rate"] > 0.5:
        return {
            "rule": "success_rate_drop",
            "severity": "critical",
            "reason": f"Error rate at {stats['error_rate']*100:.0f}% — payments failing",
        }

    if stats["logs_per_second"] > 2.0:
        return {
            "rule": "volume_spike",
            "severity": "warning",
            "reason": f"Transaction volume at {stats['logs_per_second']:.1f}/s — unusual spike",
        }

    return None


def check_auth_rules(stats: dict) -> dict | None:
    if stats["total_logs"] < 3:
        return None

    if stats["warn_count"] >= 10:
        return {
            "rule": "brute_force_attack",
            "severity": "critical",
            "reason": f"{stats['warn_count']} failed login attempts in last 60s",
        }

    if stats["error_count"] >= 5:
        return {
            "rule": "mass_lockout",
            "severity": "critical",
            "reason": f"{stats['error_count']} account lockouts in last 60s",
        }

    if stats["error_rate"] > 0.4:
        return {
            "rule": "login_success_collapse",
            "severity": "warning",
            "reason": f"Login error rate at {stats['error_rate']*100:.0f}%",
        }

    return None


def check_database_rules(stats: dict) -> dict | None:
    if stats["total_logs"] < 2:
        return None

    if stats["fatal_count"] >= 1:
        return {
            "rule": "deadlock_or_pool_exhaustion",
            "severity": "critical",
            "reason": "Fatal database error — deadlock cascade or connection pool exhausted",
        }

    if stats["error_count"] >= 3:
        return {
            "rule": "connection_pool_pressure",
            "severity": "critical",
            "reason": f"{stats['error_count']} connection errors in last 60s",
        }

    if stats["warn_count"] >= 40:
        return {
            "rule": "slow_query_pattern",
            "severity": "warning",
            "reason": f"{stats['warn_count']} slow queries in last 60s",
        }

    return None


def check_api_gateway_rules(stats: dict) -> dict | None:
    if stats["total_logs"] < 3:
        return None

    if stats["fatal_count"] >= 1:
        return {
            "rule": "circuit_breaker_open",
            "severity": "critical",
            "reason": "Circuit breaker triggered — downstream service down",
        }

    if stats["error_rate"] > 0.4:
        return {
            "rule": "5xx_cascade",
            "severity": "critical",
            "reason": f"503 error rate at {stats['error_rate']*100:.0f}% across endpoints",
        }

    if stats["warn_count"] >= 5:
        return {
            "rule": "latency_creep",
            "severity": "warning",
            "reason": f"{stats['warn_count']} high-latency requests — possible resource leak",
        }

    return None


# Maps service name to its rule-checking function
RULE_CHECKERS = {
    "payments": check_payments_rules,
    "auth": check_auth_rules,
    "database": check_database_rules,
    "api_gateway": check_api_gateway_rules,
}


def check_rules(service: str, stats: dict) -> dict | None:
    """Entry point — dispatches to the right rule checker for the service."""
    checker = RULE_CHECKERS.get(service)
    if checker is None:
        return None
    return checker(stats)