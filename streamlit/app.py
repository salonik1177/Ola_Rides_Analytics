# streamlit/app.py
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
import streamlit as st

# ------------------------------------------------------------------------------
# Page config (do this first)
# ------------------------------------------------------------------------------
st.set_page_config(page_title="Ola Rides Analytics", layout="wide")

# ------------------------------------------------------------------------------
# Robust path resolution (works locally and on Streamlit Cloud)
# ------------------------------------------------------------------------------
def _repo_root() -> Path:
    """
    Return the repository root directory (parent of /streamlit).
    """
    return Path(__file__).resolve().parent.parent


def _first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None


def get_db_path() -> Optional[Path]:
    """
    Locate an existing SQLite DB in common places inside the repo.
    """
    root = _repo_root()
    candidates = [
        root / "data" / "ola_rides.db",
        root / "sql" / "ola_rides.db",
        root / "ola_rides.db",
    ]
    return _first_existing(candidates)


def ensure_db() -> Optional[Path]:
    """
    If no DB is found, try to create one from a CSV committed to the repo.
    Creates table 'rides'.
    """
    db_path = get_db_path()
    if db_path:
        return db_path

    root = _repo_root()
    csv_candidates = [
        root / "data" / "ola_rides_clean.csv",
        root / "data" / "Ola_rides_clean.csv",
    ]
    csv_path = _first_existing(csv_candidates)
    if not csv_path:
        return None

    db_path = root / "data" / "ola_rides.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    with sqlite3.connect(db_path) as con:
        df.to_sql("rides", con, if_exists="replace", index=False)
    return db_path


def get_connection() -> sqlite3.Connection:
    """
    Return an open SQLite connection. Builds the DB from CSV if needed.
    """
    db_path = get_db_path() or ensure_db()
    if not db_path:
        # Fail with a clear message so users know what to commit.
        raise FileNotFoundError(
            "No SQLite DB found and no CSV to build it from. "
            "Please commit 'data/ola_rides.db' or 'data/ola_rides_clean.csv'."
        )
    return sqlite3.connect(db_path, check_same_thread=False)


def run_query(sql: str, params: Iterable = ()) -> pd.DataFrame:
    """
    Utility used by pages to run SELECT queries and return a DataFrame.
    """
    with get_connection() as con:
        return pd.read_sql_query(sql, con, params=list(params))

# ------------------------------------------------------------------------------
# Home page UI
# ------------------------------------------------------------------------------
st.title("🚖 Ola Rides Analytics")
st.caption("SQLite + Streamlit + Dashboard")

# Navigation buttons (Streamlit 1.25+)
try:
    c1, c2 = st.columns(2)
    with c1:
        st.page_link(
            "pages/1_SQL_Queries.py",
            label="📑 Open SQL Queries",
        )
    with c2:
        st.page_link(
            "pages/2_Dashboard.py",
            label="📊 Open Dashboard",
        )
except Exception:
    st.info("Use the sidebar to open **SQL Queries** or **Dashboard**.")

st.markdown("---")
st.subheader("What you can do")
st.markdown(
    """
- Explore the dataset with **ready-to-run SQL queries** + interactive filters.  
- View the **embedded dashboard** for executive insights.  
- Download any query result as CSV.
"""
)
