import streamlit as st
import requests
from datetime import datetime

API = "https://log-intelligence-platform.onrender.com"

SEVERITY_COLORS = {"critical": "#ef4444", "warning": "#f59e0b"}
SOURCE_ICONS    = {"rules": "📋", "ml": "🤖"}


def render_live_alerts():
    """Active anomalies right now."""
    try:
        r = requests.get(f"{API}/alerts/live", timeout=3)
        data = r.json()
    except Exception:
        st.warning("Could not load live alerts.")
        return

    alerts = data.get("active_alerts", [])

    if data.get("all_clear"):
        st.success("✅ All systems healthy — no active anomalies")
        return

    st.markdown(f"**{len(alerts)} active anomaly(s)**")

    for alert in alerts:
        anomaly  = alert.get("anomaly", {})
        service  = alert.get("service", "")
        severity = anomaly.get("severity", "warning")
        color    = SEVERITY_COLORS.get(severity, "#888")

        st.markdown(
            f"""
            <div style="border-left:4px solid {color}; background:{color}11;
                        padding:10px 14px; border-radius:4px; margin-bottom:8px;">
                <div style="font-weight:600; color:{color};">
                    🚨 [{service.upper()}] {anomaly.get('rule', '').replace('_', ' ').title()}
                </div>
                <div style="font-size:13px; color:#ccc; margin-top:4px;">
                    {anomaly.get('reason', '')}
                </div>
                <div style="font-size:11px; color:#888; margin-top:6px;">
                    severity: {severity} &nbsp;|&nbsp;
                    error_rate: {alert.get('stats', {}).get('error_rate', 0):.1%}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_alert_history():
    """Recent alerts from PostgreSQL with source labels."""
    try:
        r = requests.get(f"{API}/alerts/history?limit=20", timeout=3)
        alerts = r.json().get("alerts", [])
    except Exception:
        st.warning("Could not load alert history.")
        return

    if not alerts:
        st.info("No alerts in history yet.")
        return

    for alert in alerts:
        severity = alert.get("severity", "warning")
        source   = alert.get("source", "rules")
        color    = SEVERITY_COLORS.get(severity, "#888")
        icon     = SOURCE_ICONS.get(source, "📋")
        ts       = alert.get("created_at", "")

        # Format timestamp
        try:
            dt  = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            ts  = dt.strftime("%H:%M:%S")
        except Exception:
            ts = str(ts)[:19]

        score_str = ""
        if alert.get("anomaly_score") is not None:
            score_str = f"score: {alert['anomaly_score']:.2f} &nbsp;|&nbsp;"

        st.markdown(
            f"""
            <div style="border-left:3px solid {color}; padding:6px 12px;
                        margin-bottom:6px; font-size:13px;">
                <span style="color:{color}; font-weight:600;">
                    {icon} [{alert.get('service','').upper()}]
                </span>
                <span style="color:#ccc;"> {alert.get('rule','').replace('_',' ')}</span>
                <span style="color:#666; font-size:11px; float:right;">
                    {score_str}source: {source} | {ts}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
