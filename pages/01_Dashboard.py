# -------------------- 01_Dashboard.py (clean) --------------------
import socket
from urllib.parse import urlparse

import pandas as pd
import streamlit as st
from supabase import Client, create_client

# 1) Page config — must be FIRST Streamlit call
st.set_page_config(page_title="Comfort Dashboard", page_icon="📊", layout="wide")

# 2) Secrets → vars (strip/normalize)
SUPABASE_URL  = st.secrets["SUPABASE_URL"].strip().rstrip("/")
SUPABASE_KEY  = st.secrets["SUPABASE_KEY"].strip()
FEEDBACK_TABLE = st.secrets.get("SUPABASE_TABLE", "feedback")

# 3) One Supabase client (cached)
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# 4) Connectivity probe
host = urlparse(SUPABASE_URL).hostname or ""
try:
    _ip = socket.gethostbyname(host)
    supabase.table(FEEDBACK_TABLE).select("id").limit(1).execute()
    st.caption(f"✅ Supabase connected ({host} → {_ip})")
except Exception as e:
    st.error(f"❌ Supabase probe failed: {e}")

st.title("📊 Comfort Dashboard")

# -------- Data fetch --------
@st.cache_data(ttl=60)
def fetch_feedback(limit: int = 2000) -> pd.DataFrame:
    res = (
        supabase.table(FEEDBACK_TABLE)
        .select("*")
        .order("timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    df = pd.DataFrame(res.data or [])
    if df.empty:
        return df

    time_col = "timestamp" if "timestamp" in df.columns else ("ts" if "ts" in df.columns else None)
    if time_col:
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce", utc=True)
        df = df.dropna(subset=[time_col]).rename(columns={time_col: "timestamp"})
        df = df.sort_values("timestamp")
    return df

df = fetch_feedback()
if df.empty:
    st.info("No feedback yet. Submit some entries on the main page.")
    st.stop()

# -------- Filters --------
c1, c2, c3 = st.columns(3)
with c1:
    days_back = st.slider("Days back", 1, 30, 7)
with c2:
    room_opt = ["(all)"] + sorted(df["room"].dropna().unique()) if "room" in df else ["(all)"]
    room_sel = st.selectbox("Room", room_opt)
with c3:
    clothing_opt = ["(all)"] + sorted(df["clothing"].dropna().unique()) if "clothing" in df else ["(all)"]
    clothing_sel = st.selectbox("Clothing", clothing_opt)

cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days_back)

mask = df["timestamp"] >= cutoff
if room_sel != "(all)" and "room" in df:
    mask &= df["room"] == room_sel
if clothing_sel != "(all)" and "clothing" in df:
    mask &= df["clothing"] == clothing_sel

view = df.loc[mask].copy()
if view.empty:
    st.warning("No rows match the current filters.")
    st.stop()

# -------- KPIs --------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Submissions", len(view))
k2.metric("Rooms", view["room"].nunique() if "room" in view else 0)
k3.metric(
    "Avg thermal sensation",
    f'{view.get("thermal_sensation", pd.Series(dtype=float)).dropna().mean():.2f}'
)
k4.metric("Glare ≥ 4", int((view.get("glare_rating", pd.Series(dtype=float)) >= 4).sum()))

st.markdown("---")

# -------- Charts --------
if "thermal_sensation" in view:
    st.subheader("Thermal sensation (counts)")
    st.bar_chart(view["thermal_sensation"].value_counts().sort_index())

colA, colB = st.columns(2)
with colA:
    if "brightness" in view:
        st.subheader("Brightness")
        st.bar_chart(view["brightness"].value_counts())
with colB:
    if "clothing" in view:
        st.subheader("Clothing")
        st.bar_chart(view["clothing"].value_counts())

st.subheader("Submissions over time (hourly)")
ts = view.set_index("timestamp").resample("1H").size()
st.line_chart(ts)

st.subheader("Latest rows")
n = st.slider("Rows to show", 50, 1000, 200, step=50)
st.dataframe(view.sort_values("timestamp", ascending=False).head(n), use_container_width=True)

if st.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()
# ------------------ end file ------------------
