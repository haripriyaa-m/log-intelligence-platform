from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class ServiceHealth(BaseModel):
    service: str
    status: str                    # healthy / warning / critical
    stats: dict
    active_anomaly: Optional[dict] = None


class AlertResponse(BaseModel):
    id: int
    service: str
    rule: Optional[str]
    severity: str
    reason: str
    source: str                    # rules / ml
    anomaly_score: Optional[float]
    created_at: datetime


class LogResponse(BaseModel):
    timestamp: str
    service: str
    level: str
    message: str
    transaction_id: Optional[str]
    user_id: Optional[str]


class SystemHealth(BaseModel):
    status: str                    # healthy / degraded / critical
    services: dict[str, str]       # service → status
    active_alert_count: int
    total_logs_processed: int