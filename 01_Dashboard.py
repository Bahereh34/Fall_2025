import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta

st.set_page_config(page_title="Comfort Dashboard", page_icon="📊", layout="wide")

# Supabase (read from Streamlit secrets)
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=60)
def fetch_feedback(limit=500):
    res = supabase.table("feedback").select("*").order("timestamp", desc=True).limit(limit).execute()
    df = pd.DataFrame(res.data or [])
    if not df.empty and "timestamp" in df:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

st.title("📊 Comfort Dashboard")

df = fetch_feedback()
if df.empty:
    st.info("No feedback yet.")
    st.stop()

# ---- filters
c0, c1, c2 = st.columns([1,1,1])
with c0:
    room_opt = ["(all)"] + sorted(x for x in df["room"].dropna().unique())
    room_sel = st.selectbox("Room", room_opt)
with c1:
    days_back = st.slider("Days back", 1, 30, 7)
with c2:
    n_rows = st.slider("Rows to show", 50, 500, 200, step=50)

cutoff = datetime.utcnow() - timedelta(days=days_back)
mask = (df["timestamp"] >= cutoff)
if room_sel != "(all)":
    mask &= (df["room"] == room_sel)
view = df.loc[mask].copy()

# ---- KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Submissions", len(view))
k2.metric("Avg thermal sensation", f'{view["thermal_sensation"].dropna().mean():.2f}' if "thermal_sensation" in view else "—")
k3.metric("Glare ≥ 4", int((view.get("glare_rating", pd.Series(dtype=float)) >= 4).sum()))
k4.metric("Rooms", view["room"].nunique())

# ---- charts
st.subheader("Thermal sensation counts")
if "thermal_sensation" in view:
    st.bar_chart(view["thermal_sensation"].value_counts().sort_index())

st.subheader("Brightness")
if "brightness" in view:
    st.bar_chart(view["brightness"].value_counts())

st.subheader("Clothing")
if "clothing" in view:
    st.bar_chart(view["clothing"].value_counts())

st.subheader("Submissions over time (hourly)")
ts = view.set_index("timestamp").resample("1H").size()
st.line_chart(ts)

st.subheader("Latest rows")
st.dataframe(view.sort_values("timestamp", ascending=False).head(n_rows))
