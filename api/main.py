from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import services, alerts, logs
from api.db import redis as r_db
from api.db import postgres as pg_db

app = FastAPI(
    title="Log Intelligence Platform API",
    description="Real-time log anomaly detection and monitoring API",
    version="1.0.0",
)

# Allow the Streamlit dashboard (Week 5) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all route groups
app.include_router(services.router)
app.include_router(alerts.router)
app.include_router(logs.router)


@app.get("/")
def root():
    return {
        "name": "Log Intelligence Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "system_health": "/health",
            "services": "/services",
            "live_alerts": "/alerts/live",
            "alert_history": "/alerts/history",
            "recent_logs": "/logs/recent",
            "search_logs": "/logs/search",
        }
    }


@app.get("/health")
def system_health():
    """
    Overall system health — the first thing any monitoring tool checks.
    Aggregates service statuses into a single system verdict.
    """
    services_list = r_db.get_all_services()
    service_statuses = {}
    critical_count = 0
    warning_count = 0

    for service in services_list:
        health = r_db.get_service_health(service)
        if health:
            status = health.get("status", "unknown")
            service_statuses[service] = status
            if status == "critical":
                critical_count += 1
            elif status == "warning":
                warning_count += 1

    # Overall system status
    if critical_count > 0:
        system_status = "critical"
    elif warning_count > 0:
        system_status = "degraded"
    elif len(service_statuses) == 0:
        system_status = "unknown"
    else:
        system_status = "healthy"

    # Total logs processed
    total = pg_db.fetch_one("SELECT COUNT(*) as total FROM logs")
    total_alerts = pg_db.fetch_one("SELECT COUNT(*) as total FROM alerts")

    return {
        "status": system_status,
        "services": service_statuses,
        "active_critical": critical_count,
        "active_warnings": warning_count,
        "total_logs_processed": total["total"] if total else 0,
        "total_alerts_fired": total_alerts["total"] if total_alerts else 0,
    }