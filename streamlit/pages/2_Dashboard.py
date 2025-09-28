# streamlit_app/pages/2_Dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
from app import run_query

st.set_page_config(page_title="Ola Rides – Dashboard", layout="wide")
st.title("📊 Ola Rides – Interactive Dashboard (Streamlit)")

# booking_time stored as 'DD-MM-YYYY HH:MM' → make ISO date string in SQL
ISO_DATE = (
    "substr(booking_time,7,4) || '-' || substr(booking_time,4,2) || '-' || substr(booking_time,1,2)"
)

# --- detect table name ---
_tbls = run_query("SELECT name FROM sqlite_master WHERE type='table';")["name"].tolist()
TABLE = "rides" if "rides" in _tbls else ("ola_rides_clean" if "ola_rides_clean" in _tbls else None)
if not TABLE:
    st.error(f"No expected table. Found: {_tbls}")
    st.stop()

# --- helpers ---
def fetch_distinct(col: str) -> list[str]:
    q = f"SELECT DISTINCT {col} AS v FROM {TABLE} WHERE {col} IS NOT NULL ORDER BY 1;"
    df = run_query(q)
    return df["v"].astype(str).tolist()

def bounds():
    q = f"SELECT MIN({ISO_DATE}) AS min_dt, MAX({ISO_DATE}) AS max_dt FROM {TABLE};"
    d = run_query(q)
    return pd.to_datetime(d.min_dt.iloc[0]).date(), pd.to_datetime(d.max_dt.iloc[0]).date()

def build_where(params):
    parts, vals = [], []
    if params["date"]:
        parts.append(f"{ISO_DATE} BETWEEN ? AND ?")
        vals += [str(params["date"][0]), str(params["date"][1])]
    if params["vtypes"]:
        parts.append("vehicle_type IN (" + ",".join(["?"] * len(params["vtypes"])) + ")")
        vals += params["vtypes"]
    if params["status"]:
        parts.append("booking_status IN (" + ",".join(["?"] * len(params["status"])) + ")")
        vals += params["status"]
    if params["pays"]:
        parts.append("payment_method IN (" + ",".join(["?"] * len(params["pays"])) + ")")
        vals += params["pays"]
    if params["q"]:
        parts.append("(booking_id LIKE ? OR customer_id LIKE ?)")
        like = f"%{params['q']}%"
        vals += [like, like]
    return (" WHERE " + " AND ".join(parts)) if parts else "", vals

# --- sidebar filters ---
with st.sidebar:
    st.header("Filters")
    dmin, dmax = bounds()
    dr = st.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
    # Don’t add a predicate if the whole range is selected
    dr = None if dr and dr[0] == dmin and dr[1] == dmax else dr

    vtypes = st.multiselect("Vehicle type", fetch_distinct("vehicle_type"))
    status = st.multiselect("Booking status", fetch_distinct("booking_status"))
    pays   = st.multiselect("Payment method", fetch_distinct("payment_method"))
    q      = st.text_input("Search Booking/Customer ID")

params = {"date": dr, "vtypes": vtypes, "status": status, "pays": pays, "q": q}
W, P = build_where(params)
W1 = W if W else " WHERE 1=1"   # for clauses that append AND ...

# --- KPIs ---
kpi_sql = f"""
SELECT
  COUNT(*) AS total_rides,
  SUM(CASE WHEN booking_status='Success' THEN 1 ELSE 0 END) AS completed,
  SUM(CASE WHEN booking_status!='Success' THEN 1 ELSE 0 END) AS cancelled,
  SUM(CASE WHEN booking_status='Success' THEN booking_value ELSE 0 END) AS revenue,
  SUM(ride_distance) AS total_km,
  AVG(driver_rating) AS avg_driver_rating
FROM {TABLE} {W};
"""
k = run_query(kpi_sql, P).iloc[0]

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Rides", f"{int(k.total_rides):,}")
c2.metric("Completed", f"{int(k.completed):,}")
c3.metric("Cancelled", f"{int(k.cancelled):,}")
c4.metric("Revenue (₹)", f"₹ {k.revenue:,.0f}")
c5.metric("Total Distance (KM)", f"{k.total_km:,.0f}")
c6.metric("Avg Driver Rating", f"{k.avg_driver_rating:.2f}")

st.divider()

# --- row 1 ---
col1, col2, col3 = st.columns(3)

# Ride volume by day
q = f"""
SELECT {ISO_DATE} AS day, COUNT(*) AS total_rides
FROM {TABLE} {W}
GROUP BY {ISO_DATE}
ORDER BY day;
"""
df = run_query(q, P)
with col1:
    st.subheader("Ride Volume")
    if len(df):
        fig = px.line(df, x="day", y="total_rides")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data")

# Revenue by vehicle (completed)
q = f"""
SELECT vehicle_type, SUM(booking_value) AS revenue
FROM {TABLE} {W1} AND booking_status='Success'
GROUP BY vehicle_type
ORDER BY revenue DESC;
"""
df = run_query(q, P)
with col2:
    st.subheader("Revenue by Vehicle")
    if len(df):
        fig = px.bar(df, x="vehicle_type", y="revenue")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data")

# Revenue by payment (completed)
q = f"""
SELECT payment_method, SUM(booking_value) AS revenue
FROM {TABLE} {W1} AND booking_status='Success'
GROUP BY payment_method
ORDER BY revenue DESC;
"""
df = run_query(q, P)
with col3:
    st.subheader("Revenue by Payment")
    if len(df):
        fig = px.bar(df, x="payment_method", y="revenue")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data")

# --- row 2 ---
col4, col5, col6 = st.columns(3)

# Status breakdown
q = f"""
SELECT booking_status, COUNT(*) AS rides
FROM {TABLE} {W}
GROUP BY booking_status
ORDER BY rides DESC;
"""
df = run_query(q, P)
with col4:
    st.subheader("Status Breakdown")
    if len(df):
        fig = px.bar(df, x="rides", y="booking_status", orientation="h")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data")

# Avg customer rating by vehicle
q = f"""
SELECT vehicle_type, ROUND(AVG(customer_rating),2) AS avg_customer_rating
FROM {TABLE} {W}
GROUP BY vehicle_type
ORDER BY avg_customer_rating DESC;
"""
df = run_query(q, P)
with col5:
    st.subheader("Avg Customer Rating by Vehicle")
    if len(df):
        fig = px.bar(df, x="vehicle_type", y="avg_customer_rating")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data")

# Top 5 pickup locations
q = f"""
SELECT pickup_location, COUNT(*) AS total_rides
FROM {TABLE} {W}
GROUP BY pickup_location
ORDER BY total_rides DESC
LIMIT 5;
"""
df = run_query(q, P)
with col6:
    st.subheader("Top 5 Pickup Locations")
    if len(df):
        fig = px.bar(df, x="pickup_location", y="total_rides")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data")
