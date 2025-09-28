import streamlit as st
import pandas as pd
from App import run_query

st.title("📊 SQL Query Explorer")

# -------------------------------------------------------------------
# Auto-detect table name (expects either 'rides' or 'ola_rides_clean')
# -------------------------------------------------------------------
_tbls = run_query("SELECT name FROM sqlite_master WHERE type='table';")["name"].tolist()
TABLE = "rides" if "rides" in _tbls else ("ola_rides_clean" if "ola_rides_clean" in _tbls else None)
if not TABLE:
    st.error(f"No expected table found. Existing tables: {_tbls}")
    st.stop()

# Turn 'DD-MM-YYYY HH:MM' -> 'YYYY-MM-DD' (string) for SQLite filtering/grouping
ISO_DATE = "substr(booking_time,7,4) || '-' || substr(booking_time,4,2) || '-' || substr(booking_time,1,2)"

# ----------------- helpers -----------------
def fetch_distinct(col: str) -> list[str]:
    df = run_query(f"SELECT DISTINCT {col} AS v FROM {TABLE} WHERE {col} IS NOT NULL ORDER BY 1;")
    return df["v"].dropna().astype(str).tolist()

def fetch_date_bounds():
    q = f"SELECT MIN({ISO_DATE}) AS min_dt, MAX({ISO_DATE}) AS max_dt FROM {TABLE};"
    df = run_query(q)
    # If the table is empty, guard:
    if df.empty or pd.isna(df.iloc[0]["min_dt"]) or pd.isna(df.iloc[0]["max_dt"]):
        st.warning("No dates found in table.")
        st.stop()
    return pd.to_datetime(df.iloc[0]["min_dt"]).date(), pd.to_datetime(df.iloc[0]["max_dt"]).date()

def build_where(date_range, vehicles, statuses, pays, search_text, apply_date: bool):
    """
    Returns (where_sql, params) where where_sql starts with ' WHERE ...' or empty string.
    """
    where, params = [], []

    # Date filter using ISO reformatted date (matches 'YYYY-MM-DD')
    if apply_date and date_range:
        where.append(f"{ISO_DATE} BETWEEN ? AND ?")
        params += [str(date_range[0]), str(date_range[1])]

    if vehicles:
        where.append("vehicle_type IN (" + ",".join(["?"] * len(vehicles)) + ")")
        params += vehicles

    if statuses:
        where.append("booking_status IN (" + ",".join(["?"] * len(statuses)) + ")")
        params += statuses

    if pays:
        where.append("payment_method IN (" + ",".join(["?"] * len(pays)) + ")")
        params += pays

    if search_text:
        where.append("(booking_id LIKE ? OR customer_id LIKE ?)")
        like = f"%{search_text}%"
        params += [like, like]

    return (" WHERE " + " AND ".join(where)) if where else "", params

def normalize_where(sql: str, where_clause: str, base_params: list) -> tuple[str, list]:
    """
    If the template uses {where} and it's empty, inject ' WHERE 1=1'
    so queries that append 'AND ...' still work.
    """
    if "{where}" not in sql:
        return sql, base_params
    if where_clause.strip() == "":
        return sql.replace("{where}", " WHERE 1=1"), []
    return sql.replace("{where}", where_clause), base_params

def download_df(df: pd.DataFrame, filename="query_result.csv"):
    if df.empty:
        return
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", data=csv, file_name=filename, mime="text/csv")

# ----------------- Filters (sidebar) -----------------
with st.sidebar:
    st.header("Filters")
    min_d, max_d = fetch_date_bounds()
    date_range = st.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)

    # If user keeps full range, don't add a date predicate so first load shows data
    apply_date = not (date_range and date_range[0] == min_d and date_range[1] == max_d)

    vehicles = st.multiselect("Vehicle type", fetch_distinct("vehicle_type"))
    statuses = st.multiselect("Booking status", fetch_distinct("booking_status"))
    pays     = st.multiselect("Payment method", fetch_distinct("payment_method"))
    search_text = st.text_input("Search Booking/Customer ID")
    if st.button("Clear filters"):
        st.experimental_rerun()

# ======================================================
#                       QUERIES
# (Keeps yours + adds many probable breakdown variants)
# ======================================================
queries = {
    # OVERALL
    "Completed rides (count)":
        f"SELECT COUNT(*) AS completed_rides FROM {TABLE} {{where}} AND booking_status = 'Success';",

    "Booking status breakdown":
        f"SELECT booking_status, COUNT(*) AS rides FROM {TABLE} {{where}} GROUP BY booking_status ORDER BY rides DESC;",

    "Ride volume by day":
        f"""
        SELECT {ISO_DATE} AS day, COUNT(*) AS total_rides
        FROM {TABLE} {{where}}
        GROUP BY {ISO_DATE}
        ORDER BY day;
        """,

    "Ride volume by weekday":
        f"""
        SELECT weekday, COUNT(*) AS total_rides
        FROM {TABLE} {{where}}
        GROUP BY weekday
        ORDER BY total_rides DESC;
        """,

    "Ride volume by hour_of_day":
        f"""
        SELECT hour_of_day, COUNT(*) AS total_rides
        FROM {TABLE} {{where}}
        GROUP BY hour_of_day
        ORDER BY hour_of_day;
        """,

    # VEHICLE TYPE
    "Avg ride distance by vehicle type":
        f"SELECT vehicle_type, ROUND(AVG(ride_distance),2) AS avg_distance FROM {TABLE} {{where}} GROUP BY vehicle_type ORDER BY avg_distance DESC;",

    "Avg customer rating by vehicle type":
        f"SELECT vehicle_type, ROUND(AVG(customer_rating),2) AS avg_customer_rating FROM {TABLE} {{where}} GROUP BY vehicle_type ORDER BY avg_customer_rating DESC;",

    "Avg driver rating by vehicle type":
        f"SELECT vehicle_type, ROUND(AVG(driver_rating),2) AS avg_driver_rating FROM {TABLE} {{where}} GROUP BY vehicle_type ORDER BY avg_driver_rating DESC;",

    "Ride count by vehicle type":
        f"SELECT vehicle_type, COUNT(*) AS ride_count FROM {TABLE} {{where}} GROUP BY vehicle_type ORDER BY ride_count DESC;",

    # VEHICLE + STATUS / PAYMENT breakdowns
    "Ride count by vehicle & status":
        f"""SELECT vehicle_type, booking_status, COUNT(*) AS rides
            FROM {TABLE} {{where}}
            GROUP BY vehicle_type, booking_status
            ORDER BY rides DESC;""",

    "Ride count by vehicle & payment":
        f"""SELECT vehicle_type, payment_method, COUNT(*) AS rides
            FROM {TABLE} {{where}}
            GROUP BY vehicle_type, payment_method
            ORDER BY rides DESC;""",

    "Avg distance by vehicle & status":
        f"""SELECT vehicle_type, booking_status, ROUND(AVG(ride_distance),2) AS avg_distance
            FROM {TABLE} {{where}}
            GROUP BY vehicle_type, booking_status
            ORDER BY avg_distance DESC;""",

    # REVENUE
    "Revenue by payment method (completed only)":
        f"SELECT payment_method, SUM(booking_value) AS revenue FROM {TABLE} {{where}} AND booking_status = 'Success' GROUP BY payment_method ORDER BY revenue DESC;",

    "Revenue by vehicle type (completed only)":
        f"SELECT vehicle_type, SUM(booking_value) AS revenue FROM {TABLE} {{where}} AND booking_status = 'Success' GROUP BY vehicle_type ORDER BY revenue DESC;",

    "Top N customers by total booking value (completed only)":
        f"""
        SELECT customer_id, SUM(booking_value) AS total_value
        FROM {TABLE} {{where}} AND booking_status = 'Success'
        GROUP BY customer_id
        ORDER BY total_value DESC
        LIMIT ?;
        """,

    # CANCELLATION (force correct status & ignore payment/status conflicts)
    "Driver cancellation reasons":
        f"""
        SELECT COALESCE(NULLIF(TRIM(cancelled_by_driver_reason),''),'Unspecified') AS reason,
               COUNT(*) AS cancels
        FROM {TABLE} {{where}} AND booking_status IN ('Canceled by Driver','Driver Not Found')
        GROUP BY reason
        ORDER BY cancels DESC;
        """,

    "Customer cancellation reasons":
        f"""
        SELECT COALESCE(NULLIF(TRIM(cancelled_by_customer_reason),''),'Unspecified') AS reason,
               COUNT(*) AS cancels
        FROM {TABLE} {{where}} AND booking_status = 'Canceled by Customer'
        GROUP BY reason
        ORDER BY cancels DESC;
        """,

    # RATINGS
    "Driver ratings distribution (rounded)":
        f"SELECT ROUND(driver_rating,1) AS rating, COUNT(*) AS rides FROM {TABLE} {{where}} AND driver_rating IS NOT NULL GROUP BY rating ORDER BY rating;",

    "Customer ratings distribution (rounded)":
        f"SELECT ROUND(customer_rating,1) AS rating, COUNT(*) AS rides FROM {TABLE} {{where}} AND customer_rating IS NOT NULL GROUP BY rating ORDER BY rating;",

    # CROSS breakdowns you asked for
    "Avg customer rating by vehicle & payment":
        f"""SELECT vehicle_type, payment_method, ROUND(AVG(customer_rating),2) AS avg_customer_rating
            FROM {TABLE} {{where}}
            GROUP BY vehicle_type, payment_method
            ORDER BY avg_customer_rating DESC;""",

    "Revenue by status & payment (completed only filtered inside)":
        f"""SELECT booking_status, payment_method, SUM(booking_value) AS revenue
            FROM {TABLE} {{where}} AND booking_status = 'Success'
            GROUP BY booking_status, payment_method
            ORDER BY revenue DESC;""",
}

st.subheader("Choose a Query")
choice = st.selectbox("", list(queries.keys()))

# Optional Top-N setting
top_n = 5
if "Top N customers" in choice:
    top_n = st.number_input("Top N", min_value=1, max_value=50, value=5, step=1)

# Build WHERE + params
base_where, base_params = build_where(
    date_range=date_range,
    vehicles=vehicles,
    statuses=statuses,
    pays=pays,
    search_text=search_text,
    apply_date=apply_date
)

# Fill template and normalize WHERE if empty
sql_template = queries[choice]
sql_filled, params = normalize_where(sql_template, base_where, base_params)

# Append Top-N param
if "Top N customers" in choice:
    params = list(params) + [int(top_n)]

# Run
if st.button("Run Query"):
    df = run_query(sql_filled, params)
    st.dataframe(df, use_container_width=True)
    download_df(df)

# Debug
with st.expander("Show SQL"):
    st.code(sql_filled)
    st.write(params)

