from fastapi import APIRouter, Query
from typing import Optional
from api.db import postgres as pg_db
from api.db import redis as r_db

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/live")
def get_live_alerts():
    """
    Returns services that currently have an active anomaly.
    Reads from Redis — always reflects the latest state.
    """
    services = r_db.get_all_services()
    active = []

    for service in services:
        health = r_db.get_service_health(service)
        if health and health.get("active_anomaly"):
            active.append({
                "service": service,
                "status": health["status"],
                "anomaly": health["active_anomaly"],
                "stats": health.get("stats", {}),
            })

    return {
        "active_alerts": active,
        "count": len(active),
        "all_clear": len(active) == 0,
    }


@router.get("/history")
def get_alert_history(
    service: Optional[str] = Query(None, description="Filter by service name"),
    severity: Optional[str] = Query(None, description="Filter by severity: warning/critical"),
    source: Optional[str] = Query(None, description="Filter by source: rules/ml"),
    limit: int = Query(50, le=200, description="Max results to return"),
):
    """
    Returns historical alerts from PostgreSQL with optional filters.
    Supports filtering by service, severity, and detection source.
    """
    conditions = []
    params = []

    if service:
        conditions.append("service = %s")
        params.append(service)
    if severity:
        conditions.append("severity = %s")
        params.append(severity)
    if source:
        conditions.append("source = %s")
        params.append(source)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
        SELECT id, service, rule, severity, reason, source,
               anomaly_score, created_at
        FROM alerts
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s
    """
    params.append(limit)

    alerts = pg_db.fetch_all(query, params)

    return {
        "alerts": alerts,
        "count": len(alerts),
        "filters": {
            "service": service,
            "severity": severity,
            "source": source,
        }
    }


@router.get("/summary")
def get_alert_summary():
    """
    Returns alert counts grouped by service and severity.
    Useful for dashboard overview panels.
    """
    by_service = pg_db.fetch_all("""
        SELECT service, severity, COUNT(*) as count
        FROM alerts
        GROUP BY service, severity
        ORDER BY service, severity
    """)

    by_source = pg_db.fetch_all("""
        SELECT source, COUNT(*) as count
        FROM alerts
        GROUP BY source
    """)

    total = pg_db.fetch_one("SELECT COUNT(*) as total FROM alerts")

    return {
        "total_alerts": total["total"] if total else 0,
        "by_service": by_service,
        "by_source": by_source,
    }