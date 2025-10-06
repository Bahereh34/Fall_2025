import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta

st.set_page_config(page_title="Sensors Dashboard", page_icon="📟", layout="wide")

# --- Supabase client from secrets ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=60)
def fetch_sensors(limit=5000):
    res = (supabase
           .table("sensor_readings")
           .select("*")
           .order("ts", desc=True)
           .limit(limit)
           .execute())
    df = pd.DataFrame(res.data or [])
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"])
    return df

st.title("📟 Sensor Readings")

df = fetch_sensors()
if df.empty:
    st.info("No sensor data yet.")
    st.stop()

# ---- Filters
c0, c1, c2, c3 = st.columns([1,1,1,1])
with c0:
    days_back = st.slider("Days back", 1, 30, 3)
with c1:
    devices = ["(all)"] + sorted(df["device_id"].dropna().unique())
    dev_sel = st.selectbox("Device", devices)
with c2:
    rooms = ["(all)"] + sorted(df["room"].dropna().unique())
    room_sel = st.selectbox("Room", rooms)
with c3:
    resample_rule = st.selectbox("Time bin", ["5min","15min","30min","1H","1D"], index=2)

cut = datetime.utcnow() - timedelta(days=days_back)
mask = df["ts"] >= cut
if dev_sel != "(all)":
    mask &= df["device_id"] == dev_sel
if room_sel != "(all)":
    mask &= df["room"] == room_sel
view = df.loc[mask].copy().sort_values("ts")

# ---- KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Rows", len(view))
k2.metric("Devices", view["device_id"].nunique())
k3.metric("Avg CO₂ (ppm)", f'{view["co2_ppm"].dropna().mean():.0f}' if "co2_ppm" in view else "—")
k4.metric("Avg Lux", f'{view["lux"].dropna().mean():.0f}' if "lux" in view else "—")

# ---- Charts (resampled)
if not view.empty:
    rs = view.set_index("ts").resample(resample_rule).mean(numeric_only=True)

    st.subheader("Temperature (°C)")
    st.line_chart(rs["temp_c"] if "temp_c" in rs else rs)

    st.subheader("Relative Humidity (%)")
    st.line_chart(rs["rh"] if "rh" in rs else rs)

    st.subheader("CO₂ (ppm)")
    st.line_chart(rs["co2_ppm"] if "co2_ppm" in rs else rs)

    st.subheader("Illuminance (lux)")
    st.line_chart(rs["lux"] if "lux" in rs else rs)

st.subheader("Latest rows")
st.dataframe(view.sort_values("ts", ascending=False).head(200))

with st.expander("Manual test insert (for debugging)"):
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: device_id = st.text_input("device_id", "esp32-classroom-01")
    with c2: room = st.text_input("room", "Lab-101")
    with c3: temp_c = st.number_input("temp_c", value=23.0)
    with c4: rh = st.number_input("rh", value=45.0)
    with c5: co2_ppm = st.number_input("co2_ppm", value=700)
    with c6: lux = st.number_input("lux", value=500)
    if st.button("Insert test row"):
        try:
            supabase.table("sensor_readings").insert({
                "device_id": device_id, "room": room,
                "temp_c": temp_c, "rh": rh, "co2_ppm": co2_ppm, "lux": lux
            }).execute()
            st.success("Row inserted ✅")
            st.cache_data.clear()  # refresh
        except Exception as e:
            st.error(f"Insert failed: {e}")
