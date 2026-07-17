import streamlit as st
import requests

API = "https://log-intelligence-dashboard.onrender.com"

STATUS_COLORS = {
    "healthy":  "#22c55e",
    "warning":  "#f59e0b",
    "critical": "#ef4444",
    "unknown":  "#6b7280",
    "degraded": "#f59e0b",
}

STATUS_ICONS = {
    "healthy":  "✅",
    "warning":  "⚠️",
    "critical": "🚨",
    "unknown":  "❓",
    "degraded": "⚠️",
}


def render_system_health():
    """Top banner showing overall system status."""
    try:
        r = requests.get(f"{API}/health", timeout=3)
        data = r.json()
    except Exception:
        st.error("Cannot reach API — is it running on port 8000?")
        return

    status = data.get("status", "unknown")
    color  = STATUS_COLORS.get(status, "#6b7280")
    icon   = STATUS_ICONS.get(status, "❓")

    st.markdown(
        f"""
        <div style="background:{color}22; border:2px solid {color};
                    border-radius:10px; padding:16px 24px; margin-bottom:16px;">
            <h2 style="margin:0; color:{color};">
                {icon} System Status: {status.upper()}
            </h2>
            <p style="margin:4px 0 0; color:#888; font-size:14px;">
                Logs processed: {data.get('total_logs_processed', 0):,} &nbsp;|&nbsp;
                Alerts fired: {data.get('total_alerts_fired', 0):,} &nbsp;|&nbsp;
                Critical: {data.get('active_critical', 0)} &nbsp;|&nbsp;
                Warnings: {data.get('active_warnings', 0)}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_service_cards():
    """One card per service showing current health."""
    try:
        r = requests.get(f"{API}/services", timeout=3)
        data = r.json().get("services", {})
    except Exception:
        st.warning("Could not load service health.")
        return

    cols = st.columns(len(data) if data else 1)

    for idx, (service, info) in enumerate(sorted(data.items())):
        status  = info.get("status", "unknown")
        color   = STATUS_COLORS.get(status, "#6b7280")
        icon    = STATUS_ICONS.get(status, "❓")
        stats   = info.get("stats", {})
        anomaly = info.get("active_anomaly")

        with cols[idx]:
            st.markdown(
                f"""
                <div style="background:{color}15; border:1.5px solid {color};
                            border-radius:8px; padding:12px; text-align:center;">
                    <div style="font-size:22px;">{icon}</div>
                    <div style="font-weight:600; font-size:15px; margin:4px 0;">
                        {service}
                    </div>
                    <div style="color:{color}; font-size:13px; font-weight:500;">
                        {status.upper()}
                    </div>
                    <hr style="border-color:{color}33; margin:8px 0;">
                    <div style="font-size:12px; color:#888; text-align:left;">
                        error rate: <b>{stats.get('error_rate', 0):.1%}</b><br>
                        logs/60s: <b>{stats.get('total_logs', 0)}</b><br>
                        fatals: <b>{stats.get('fatal_count', 0)}</b>
                    </div>
                    {"<div style='margin-top:8px; font-size:11px; color:" + color + ";'>" + anomaly.get('rule','') + "</div>" if anomaly else ""}
                </div>
                """,
                unsafe_allow_html=True,
            )