import streamlit as st
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.components.health_gauges import render_system_health, render_service_cards
from dashboard.components.alert_panel   import render_live_alerts, render_alert_history
from dashboard.components.live_feed     import render_live_feed
from dashboard.components.trend_charts  import (
    render_error_rate_chart,
    render_log_volume_chart,
    render_alert_breakdown,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Log Intelligence Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 Log Intelligence")
    st.markdown("Real-time anomaly detection across 4 microservices.")
    st.divider()

    refresh_rate = st.slider(
        "Auto-refresh (seconds)", min_value=3, max_value=30, value=5
    )

    service_filter = st.selectbox(
        "Filter logs by service",
        ["All", "payments", "auth", "database", "api_gateway"]
    )

    lookback = st.selectbox(
        "Chart lookback window",
        [5, 10, 15, 30],
        index=2,
        format_func=lambda x: f"{x} minutes"
    )

    st.divider()
    st.markdown("**Stack**")
    st.markdown("""
    - 🟡 Kafka streaming
    - 🐍 Python pipeline
    - 🤖 Isolation Forest (ONNX)
    - ⚡ FastAPI backend
    - 🐘 PostgreSQL + Redis
    """)

    st.divider()
    if st.button("🚨 Inject: Brute Force", use_container_width=True):
        import subprocess
        subprocess.Popen(
            ["python", "simulator/scenarios.py", "--scenario", "brute_force"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        st.success("Brute force injected!")

    if st.button("💳 Inject: Gateway Failure", use_container_width=True):
        import subprocess
        subprocess.Popen(
            ["python", "simulator/scenarios.py", "--scenario", "gateway_failure"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        st.success("Gateway failure injected!")

    if st.button("🗄️ Inject: DB Deadlock", use_container_width=True):
        import subprocess
        subprocess.Popen(
            ["python", "simulator/scenarios.py", "--scenario", "db_deadlock"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        st.success("DB deadlock injected!")

# ── Main layout ───────────────────────────────────────────────────────────────
st.title("🔍 Real-Time Log Intelligence Platform")
st.caption("Live anomaly detection · Rules + ML · 4 microservices")

# Row 1: system health banner
render_system_health()

# Row 2: service cards
st.subheader("Service Health")
render_service_cards()

st.divider()

# Row 3: alerts + live feed side by side
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("🚨 Active Anomalies")
    render_live_alerts()

    st.subheader("📋 Alert History")
    render_alert_history()

with col_right:
    st.subheader("📜 Live Log Feed")
    render_live_feed(
        service_filter=service_filter if service_filter != "All" else None,
        limit=30
    )

st.divider()

# Row 4: charts
st.subheader("📈 Trends")
col_chart1, col_chart2, col_chart3 = st.columns([2, 1, 1])

with col_chart1:
    render_error_rate_chart(last_minutes=lookback)

with col_chart2:
    render_log_volume_chart(last_minutes=lookback)

with col_chart3:
    render_alert_breakdown()

# ── Auto-refresh ──────────────────────────────────────────────────────────────
st.divider()
st.caption(f"Auto-refreshing every {refresh_rate}s · "
           f"Last updated: {time.strftime('%H:%M:%S')}")

time.sleep(refresh_rate)
st.rerun()