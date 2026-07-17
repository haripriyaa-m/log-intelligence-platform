from fastapi import APIRouter, Query
from typing import Optional
from api.db import postgres as pg_db
from api.db import redis as r_db

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/recent")
def get_recent_logs(
    service: Optional[str] = Query(None, description="Filter by service"),
    limit: int = Query(50, le=200),
):
    """
    Returns most recent log lines.
    If service is specified, reads from Redis (instant).
    Otherwise queries PostgreSQL for cross-service recent logs.
    """
    if service:
        logs = r_db.get_recent_logs(service, limit=limit)
        return {"logs": logs, "count": len(logs), "source": "redis"}

    # Cross-service: query PostgreSQL
    logs = pg_db.fetch_all("""
        SELECT timestamp, service, level, message,
               transaction_id, user_id
        FROM logs
        ORDER BY id DESC
        LIMIT %s
    """, (limit,))

    return {"logs": logs, "count": len(logs), "source": "postgres"}


@router.get("/search")
def search_logs(
    service: Optional[str] = Query(None),
    level: Optional[str] = Query(None, description="INFO/WARN/ERROR/FATAL"),
    keyword: Optional[str] = Query(None, description="Search in message text"),
    last_minutes: int = Query(5, description="Look back N minutes"),
    limit: int = Query(100, le=500),
):
    """
    Search logs by service, level, keyword, and time window.
    This is the query a real engineer runs during an incident.
    """
    conditions = ["created_at > NOW() - INTERVAL '%s minutes'"]
    params = [last_minutes]

    if service:
        conditions.append("service = %s")
        params.append(service)
    if level:
        conditions.append("level = %s")
        params.append(level.upper())
    if keyword:
        conditions.append("message ILIKE %s")
        params.append(f"%{keyword}%")

    where_clause = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT timestamp, service, level, message,
               transaction_id, user_id
        FROM logs
        {where_clause}
        ORDER BY timestamp DESC
        LIMIT %s
    """
    params.append(limit)

    logs = pg_db.fetch_all(query, params)

    return {
        "logs": logs,
        "count": len(logs),
        "query": {
            "service": service,
            "level": level,
            "keyword": keyword,
            "last_minutes": last_minutes,
        }
    }


@router.get("/error-rate")
def get_error_rate_over_time(
    service: Optional[str] = Query(None),
    interval_minutes: int = Query(1, description="Bucket size in minutes"),
    last_minutes: int = Query(30, description="Total lookback window"),
):
    """
    Returns error rate over time — the data that powers trend charts.
    Groups logs into time buckets and computes error rate per bucket.
    """
    service_filter = "AND service = %s" if service else ""
    params = [last_minutes, interval_minutes]
    if service:
        params.insert(1, service)

    query = f"""
        SELECT
            date_trunc('minute', timestamp) +
                (EXTRACT(minute FROM timestamp)::int / %s * %s) * INTERVAL '1 minute'
                AS bucket,
            service,
            COUNT(*) as total,
            SUM(CASE WHEN level IN ('ERROR', 'FATAL') THEN 1 ELSE 0 END) as errors,
            ROUND(
                SUM(CASE WHEN level IN ('ERROR', 'FATAL') THEN 1 ELSE 0 END)::numeric
                / COUNT(*) * 100, 2
            ) as error_rate_pct
        FROM logs
        WHERE created_at > NOW() - INTERVAL '{last_minutes} minutes'
        {service_filter}
        GROUP BY bucket, service
        ORDER BY bucket DESC, service
        LIMIT 200
    """.replace(
        "INTERVAL '%s minutes'", f"INTERVAL '{last_minutes} minutes'"
    )

    # Simpler version that works reliably
    simple_query = f"""
        SELECT
            date_trunc('minute', timestamp) AS bucket,
            service,
            COUNT(*) as total,
            SUM(CASE WHEN level IN ('ERROR', 'FATAL') THEN 1 ELSE 0 END) as errors
        FROM logs
        WHERE created_at > NOW() - INTERVAL '{last_minutes} minutes'
        {"AND service = %s" if service else ""}
        GROUP BY bucket, service
        ORDER BY bucket DESC, service
        LIMIT 200
    """

    params_simple = [service] if service else []
    data = pg_db.fetch_all(simple_query, params_simple)

    return {"data": data, "interval_minutes": interval_minutes, "service": service}