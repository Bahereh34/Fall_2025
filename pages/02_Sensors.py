import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.set_page_config(page_title="Sensors Dashboard", page_icon="📟", layout="wide")
st.title("📟 Sensor Readings")

# --- Supabase client from Streamlit secrets ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=60)
def fetch_sensors(limit=5000) -> pd.DataFrame:
    res = (
        supabase.table("sensor_readings")
        .select("*")
        .order("ts", desc=True)
        .limit(limit)
        .execute()
    )
    df = pd.DataFrame(res.data or [])

    if df.empty:
        return df

    # --- Normalize the time column and dtype ---
    tscol = "ts" if "ts" in df.columns else ("timestamp" if "timestamp" in df.columns else None)
    if tscol is None:
        return df  # (no time column yet)

    # parse to timezone-aware UTC datetimes then rename to 'ts'
    df[tscol] = pd.to_datetime(df[tscol], errors="coerce", utc=True)
    df = df.dropna(subset=[tscol]).rename(columns={tscol: "ts"})
    df = df.sort_values("ts")
    return df

df = fetch_sensors()

if df.empty:
    st.info("No sensor data yet. Use the insert tester below or your device to post readings.")
else:
    # ---- Filters ------------------------------------------------------
    c0, c1, c2 = st.columns(3)
    with c0:
        days_back = st.slider("Days back", 1, 30, 7)
    with c1:
        devices = ["(all)"] + sorted(df["device_id"].dropna().unique())
        dev_sel = st.selectbox("Device", devices)
    with c2:
        rooms = ["(all)"] + sorted(df["room"].dropna().unique())
        room_sel = st.selectbox("Room", rooms)

    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days_back)

    mask = df["ts"] >= cutoff
    if dev_sel != "(all)":
        mask &= df["device_id"] == dev_sel
    if room_sel != "(all)":
        mask &= df["room"] == room_sel

    view = df.loc[mask].copy()

    # ---- KPIs ---------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Rows", len(view))
    k2.metric("Devices", view["device_id"].nunique())
    k3.metric("Avg CO₂ (ppm)", f'{view.get("co2_ppm", pd.Series(dtype=float)).dropna().mean():.0f}')
    k4.metric("Avg Lux", f'{view.get("lux", pd.Series(dtype=float)).dropna().mean():.0f}')

    # ---- Charts -------------------------------------------------------
    if not view.empty:
        bin_rule = st.selectbox("Time bin", ["5min", "15min", "30min", "1H", "1D"], index=2)
        rs = view.set_index("ts").resample(bin_rule).mean(numeric_only=True)

        st.subheader("Temperature (°C)")
        st.line_chart(rs.get("temp_c"))

        st.subheader("Relative Humidity (%)")
        st.line_chart(rs.get("rh"))

        st.subheader("CO₂ (ppm)")
        st.line_chart(rs.get("co2_ppm"))

        st.subheader("Illuminance (lux)")
        st.line_chart(rs.get("lux"))

    st.subheader("Latest rows")
    st.dataframe(view.sort_values("ts", ascending=False).head(200), use_container_width=True)

# ---- Manual test insert (for debugging) -----------------
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
            st.cache_data.clear()   # clear cached fetch_sensors()
            st.rerun()              # <— force a fresh run so charts pick it up
        except Exception as e:
            st.error(f"Insert failed: {e}")
