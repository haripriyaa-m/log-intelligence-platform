import streamlit as st
import requests
import plotly.graph_objects as go
import plotly.express as px
from collections import defaultdict

API = "https://log-intelligence-dashboard.onrender.com"

SERVICE_COLORS = {
    "payments":    "#3b82f6",
    "auth":        "#8b5cf6",
    "database":    "#f59e0b",
    "api_gateway": "#10b981",
}


def render_error_rate_chart(last_minutes: int = 15):
    """Line chart showing error rate over time per service."""
    try:
        r    = requests.get(
            f"{API}/logs/error-rate?last_minutes={last_minutes}",
            timeout=3
        )
        data = r.json().get("data", [])
    except Exception:
        st.warning("Could not load trend data.")
        return

    if not data:
        st.info("Not enough data yet for trend chart — wait a minute and refresh.")
        return

    # Group by service
    by_service = defaultdict(lambda: {"buckets": [], "errors": [], "totals": []})
    for row in data:
        svc = row.get("service", "")
        by_service[svc]["buckets"].append(str(row.get("bucket", ""))[:16])
        by_service[svc]["errors"].append(int(row.get("errors", 0)))
        by_service[svc]["totals"].append(int(row.get("total", 1)))

    fig = go.Figure()

    for service, series in by_service.items():
        # Compute error rate pct
        rates = [
            round(e / max(t, 1) * 100, 1)
            for e, t in zip(series["errors"], series["totals"])
        ]
        # Reverse so time goes left → right
        buckets = list(reversed(series["buckets"]))
        rates   = list(reversed(rates))

        fig.add_trace(go.Scatter(
            x=buckets,
            y=rates,
            name=service,
            mode="lines+markers",
            line=dict(color=SERVICE_COLORS.get(service, "#888"), width=2),
            marker=dict(size=5),
        ))

    fig.update_layout(
        title=f"Error Rate % — Last {last_minutes} Minutes",
        xaxis_title="Time",
        yaxis_title="Error Rate %",
        yaxis=dict(range=[0, 100]),
        plot_bgcolor="#111827",
        paper_bgcolor="#111827",
        font=dict(color="#d1d5db"),
        legend=dict(bgcolor="#1f2937"),
        height=300,
        margin=dict(l=40, r=20, t=40, b=40),
    )
    fig.update_xaxes(gridcolor="#1f2937", tickangle=45)
    fig.update_yaxes(gridcolor="#1f2937")

    st.plotly_chart(fig, use_container_width=True)


def render_log_volume_chart(last_minutes: int = 15):
    """Bar chart showing log volume per service."""
    try:
        r    = requests.get(
            f"{API}/logs/error-rate?last_minutes={last_minutes}",
            timeout=3
        )
        data = r.json().get("data", [])
    except Exception:
        st.warning("Could not load volume data.")
        return

    if not data:
        return

    # Sum total logs per service
    totals = defaultdict(int)
    for row in data:
        totals[row.get("service", "")] += int(row.get("total", 0))

    services = list(totals.keys())
    counts   = [totals[s] for s in services]
    colors   = [SERVICE_COLORS.get(s, "#888") for s in services]

    fig = go.Figure(go.Bar(
        x=services,
        y=counts,
        marker_color=colors,
        text=counts,
        textposition="auto",
    ))

    fig.update_layout(
        title=f"Log Volume — Last {last_minutes} Minutes",
        plot_bgcolor="#111827",
        paper_bgcolor="#111827",
        font=dict(color="#d1d5db"),
        height=250,
        margin=dict(l=40, r=20, t=40, b=40),
    )
    fig.update_yaxes(gridcolor="#1f2937")

    st.plotly_chart(fig, use_container_width=True)


def render_alert_breakdown():
    """Pie chart showing alerts by source (rules vs ml)."""
    try:
        r    = requests.get(f"{API}/alerts/summary", timeout=3)
        data = r.json()
    except Exception:
        return

    by_source = data.get("by_source", [])
    if not by_source:
        return

    labels = [row["source"] for row in by_source]
    values = [row["count"] for row in by_source]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker_colors=["#3b82f6", "#8b5cf6"],
    ))

    fig.update_layout(
        title="Alerts by Detection Source",
        plot_bgcolor="#111827",
        paper_bgcolor="#111827",
        font=dict(color="#d1d5db"),
        height=250,
        margin=dict(l=20, r=20, t=40, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)