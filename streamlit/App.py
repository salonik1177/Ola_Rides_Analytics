# streamlit_app/app.py
import sqlite3
import pandas as pd
import streamlit as st

# ---------- DB helpers (pages import run_query from here) ----------
DB_PATH = r"C:\Users\salon\OneDrive\Desktop\Labmentix Internship\Ola Ride Analysis\ola_ride_project\data\ola_rides.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def run_query(q: str, params: list | tuple | None = None) -> pd.DataFrame:
    con = get_connection()
    try:
        return pd.read_sql_query(q, con, params=params or [])
    finally:
        con.close()

# ---------- Home page UI ----------
st.set_page_config(page_title="Ola Rides Analytics", layout="wide")

st.title("🚖 Ola Rides Analytics")
st.caption("SQLite + Streamlit + Dashboard")

# If your Streamlit version supports page_link, show buttons:
try:
    col1, col2 = st.columns(2)
    with col1:
        st.page_link("pages/1_SQL_Queries.py", label="📊 Open SQL Queries", icon=":material/table_chart:")
    with col2:
        st.page_link("pages/2_Dashboard.py", label="📈 Open Dashboard", icon=":material/monitoring:")
except Exception:
    st.write("Use the sidebar to open **SQL Queries** or **Dashboard** (under 'app').")

st.markdown("---")
st.subheader("What you can do")
st.markdown("""
- Explore the dataset with **ready-to-run SQL queries** + interactive filters.
- View the **embedded dashboard** for executive insights.
- Download any query result as CSV.
""")
