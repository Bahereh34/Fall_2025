import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta

st.set_page_config(page_title="Comfort Dashboard", page_icon="📊", layout="wide")
st.title("📊 Comfort Dashboard")

# --- Supabase client from Streamlit secrets ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Data loader ---
@st.cache_data(ttl=60)
def fetch_feedback(limit=2000):
    try:
        res = (
            supabase.table("feedback")
            .select("*")
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        df = pd.DataFrame(res.data or [])
        if not df.empty and "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
            df = df.sort_values("timestamp")
        return df
    except Exception as e:
        st.error(f"DB error: {e}")
        return pd.DataFrame()

df = fetch_feedback()

if df.empty:
    st.info("No feedback yet. Submit a few entries from the main page.")
    st.stop()

# --- Filters ---
left, mid, right = st.columns(3)
with left:
    days_back = st.slider("Days back", 1, 30, 7)
with mid:
    room_opt = ["(all)"] + sorted([r for r in df["room"].dropna().unique()])
    room_sel = st.selectbox("Room", room_opt)
with right:
    clothing_opt = ["(all)"] + sorted([c for c in df["clothing"].dropna().unique()])
    clothing_sel = st.selectbox("Clothing", clothing_opt)

cutoff = datetime.utcnow() - timedelta(days=days_back)
mask = (df["timestamp"] >= cutoff)

if room_sel != "(all)":
    mask &= (df["room"] == room_sel)
if clothing_sel != "(all)":
    mask &= (df["clothing"] == clothing_sel)

view = df.loc[mask].copy()

if view.empty:
    st.warning("No rows match the current filters.")
    st.stop()

# --- KPIs ---
k1, k2, k3, k4 = st.columns(4)
k1.metric("Submissions", len(view))
k2.metric("Rooms", view["room"].nunique())
k3.metric("Avg thermal sensation", f'{view.get("thermal_sensation", pd.Series(dtype=float)).dropna().mean():.2f}')
k4.metric("Glare ≥ 4", int((view.get("glare_rating", pd.Series(dtype=float)) >= 4).sum()))

st.markdown("---")

# --- Charts ---
st.subheader("Thermal sensation (counts)")
if "thermal_sensation" in view:
    st.bar_chart(view["thermal_sensation"].value_counts().sort_index())

colA, colB = st.columns(2)
with colA:
    st.subheader("Brightness")
    if "brightness" in view:
        st.bar_chart(view["brightness"].value_counts())

with colB:
    st.subheader("Clothing")
    if "clothing" in view:
        st.bar_chart(view["clothing"].value_counts())

st.subheader("Submissions over time (hourly)")
ts = view.set_index("timestamp").resample("1H").size()
st.line_chart(ts)

# --- Table + export ---
st.subheader("Latest rows")
n = st.slider("Rows to show", 50, 1000, 200, step=50)
show = view.sort_values("timestamp", ascending=False).head(n)
st.dataframe(show, use_container_width=True)

csv = show.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download CSV", data=csv, file_name="feedback_filtered.csv", mime="text/csv")

# utility
colR1, colR2 = st.columns(2)
with colR1:
    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
