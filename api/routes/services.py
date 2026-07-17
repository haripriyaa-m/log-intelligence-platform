from fastapi import APIRouter, HTTPException
from api.db import redis as r_db
from api.db import postgres as pg_db

router = APIRouter(prefix="/services", tags=["services"])


@router.get("/")
def get_all_services():
    """
    Returns current health status of all known services.
    Reads from Redis — sub-millisecond response.
    """
    services = r_db.get_all_services()
    if not services:
        return {"services": [], "message": "No services seen yet — is the pipeline running?"}

    result = {}
    for service in sorted(services):
        health = r_db.get_service_health(service)
        if health:
            result[service] = {
                "status": health.get("status", "unknown"),
                "stats": health.get("stats", {}),
                "active_anomaly": health.get("active_anomaly"),
            }

    return {"services": result, "count": len(result)}


@router.get("/{service}")
def get_service_detail(service: str, log_limit: int = 20):
    """
    Returns detailed health + recent logs for one service.
    Combines Redis (live state) + recent log buffer.
    """
    health = r_db.get_service_health(service)
    if not health:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service}' not found. Known services: payments, auth, database, api_gateway"
        )

    recent_logs = r_db.get_recent_logs(service, limit=log_limit)

    return {
        "service": service,
        "status": health.get("status", "unknown"),
        "stats": health.get("stats", {}),
        "active_anomaly": health.get("active_anomaly"),
        "recent_logs": recent_logs,
    }


@router.get("/{service}/stats")
def get_service_stats(service: str):
    """Returns just the rolling window stats for a service."""
    health = r_db.get_service_health(service)
    if not health:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
    return {"service": service, "stats": health.get("stats", {})}