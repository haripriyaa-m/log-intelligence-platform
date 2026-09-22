import streamlit as st
import requests

API = "https://log-intelligence-platform.onrender.com"

LEVEL_COLORS = {
    "INFO":    "#6b7280",
    "WARN":    "#f59e0b",
    "ERROR":   "#ef4444",
    "FATAL":   "#dc2626",
    "UNKNOWN": "#6b7280",
}

SERVICE_COLORS = {
    "payments":    "#3b82f6",
    "auth":        "#8b5cf6",
    "database":    "#f59e0b",
    "api_gateway": "#10b981",
}


def render_live_feed(service_filter: str = None, limit: int = 30):
    """Scrolling live log feed, colour-coded by level."""
    try:
        url = f"{API}/logs/recent?limit={limit}"
        if service_filter and service_filter != "All":
            url += f"&service={service_filter}"
        r    = requests.get(url, timeout=3)
        logs = r.json().get("logs", [])
    except Exception:
        st.warning("Could not load live logs.")
        return

    if not logs:
        st.info("No logs yet — is the simulator running?")
        return

    lines = []
    for log in logs:
        level   = log.get("level", "INFO")
        service = log.get("service", "")
        msg     = log.get("message", "")
        ts      = str(log.get("timestamp", ""))[:19]

        level_color   = LEVEL_COLORS.get(level, "#6b7280")
        service_color = SERVICE_COLORS.get(service, "#6b7280")

        lines.append(
            f'<div style="font-family:monospace; font-size:12px; '
            f'padding:3px 0; border-bottom:1px solid #1f2937;">'
            f'<span style="color:#6b7280;">{ts}</span> '
            f'<span style="color:{level_color}; font-weight:600; '
            f'min-width:45px; display:inline-block;">{level}</span> '
            f'<span style="color:{service_color}; min-width:90px; '
            f'display:inline-block;">[{service}]</span> '
            f'<span style="color:#d1d5db;">{msg[:100]}</span>'
            f'</div>'
        )

    feed_html = (
        '<div style="background:#111827; padding:12px; border-radius:8px; '
        'height:350px; overflow-y:auto; border:1px solid #374151;">'
        + "".join(lines)
        + "</div>"
    )

    st.markdown(feed_html, unsafe_allow_html=True)
