# -------------------- pages/02_Sensors.py --------------------
import socket
from urllib.parse import urlparse
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from supabase import Client, create_client

try:
    from postgrest import APIError
except Exception:
    class APIError(Exception):
        pass


# 1) Page config
st.set_page_config(page_title="Sensors Dashboard", page_icon="📟", layout="wide")
st.title("📟 Sensor Readings")

# 2) Secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"].strip().rstrip("/")
SUPABASE_KEY = st.secrets["SUPABASE_KEY"].strip()
SENSORS_TABLE = st.secrets.get("SENSORS_TABLE", "sensor_readings")

# 3) Supabase client
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# 4) Connectivity probe
host = urlparse(SUPABASE_URL).hostname or ""
try:
    _ip = socket.gethostbyname(host)
    supabase.table(SENSORS_TABLE).select("device_id").limit(1).execute()
except Exception as e:
    st.error(f"❌ Supabase probe failed: {e}")

# 5) Fetch data
@st.cache_data(ttl=60)
def fetch_sensors(limit: int = 5000) -> pd.DataFrame:
    try:
        res = (
            supabase.table(SENSORS_TABLE)
            .select("*")
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        data = res.data or []
    except APIError as e:
        st.error(
            f"Supabase error → code={getattr(e, 'code', None)} | "
            f"message={getattr(e, 'message', e)} | details={getattr(e, 'details', None)}"
        )
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Unexpected fetch error: {e}")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    if df.empty:
        return df

    if "timestamp" not in df.columns:
        st.warning("No 'timestamp' column found in sensor_readings.")
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    return df


df = fetch_sensors()

# 6) Empty state
if df.empty:
    st.info("No sensor data yet. Use the insert tester below or your device to post readings.")
else:
    # 7) Filters
    top1, top2, top3 = st.columns(3)

    with top1:
        days_back = st.slider("Days back", min_value=1, max_value=30, value=7)

    with top2:
        dev_series = df["device_id"].astype(str) if "device_id" in df.columns else pd.Series(dtype=str)
        dev_opt = ["(all)"] + sorted(dev_series.dropna().unique().tolist())
        dev_sel = st.selectbox("Device", dev_opt)

    with top3:
        room_series = df["room"].astype(str) if "room" in df.columns else pd.Series(dtype=str)
        room_opt = ["(all)"] + sorted(room_series.dropna().unique().tolist())
        room_sel = st.selectbox("Room", room_opt)

    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days_back)
    mask = df["timestamp"] >= cutoff

    if dev_sel != "(all)" and "device_id" in df.columns:
        mask &= df["device_id"].astype(str) == dev_sel

    if room_sel != "(all)" and "room" in df.columns:
        mask &= df["room"].astype(str) == room_sel

    view = df.loc[mask].copy()

    # 8) KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Rows", int(len(view)))
    k2.metric("Devices", int(view["device_id"].nunique()) if "device_id" in view.columns else 0)

    avg_co2 = view["co2_ppm"].dropna().mean() if "co2_ppm" in view.columns else None
    avg_lux = view["lux"].dropna().mean() if "lux" in view.columns else None

    k3.metric("Avg CO₂ (ppm)", f"{avg_co2:.0f}" if avg_co2 is not None and pd.notna(avg_co2) else "—")
    k4.metric("Avg Lux", f"{avg_lux:.0f}" if avg_lux is not None and pd.notna(avg_lux) else "—")

    # 9) Charts
    if not view.empty:
        bin_rule = st.selectbox("Time bin", ["5min", "15min", "30min", "1H", "1D"], index=2)
        rs = view.set_index("timestamp").resample(bin_rule).mean(numeric_only=True)

        if "temp_c" in rs.columns:
            st.subheader("Temperature (°C)")
            st.line_chart(rs["temp_c"])

        if "rh_percent" in rs.columns:
            st.subheader("Relative Humidity (%)")
            st.line_chart(rs["rh_percent"])

        if "co2_ppm" in rs.columns:
            st.subheader("CO₂ (ppm)")
            st.line_chart(rs["co2_ppm"])

        if "lux" in rs.columns:
            st.subheader("Illuminance (lux)")
            st.line_chart(rs["lux"])

    # 10) Latest rows
    st.subheader("Latest rows")
    st.dataframe(
        view.sort_values("timestamp", ascending=False).head(200),
        use_container_width=True,
        height=380,
    )

# 11) Manual test insert
with st.expander("Manual test insert (for debugging)"):
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        device_id = st.text_input("device_id", "esp32-classroom-01")
    with c2:
        room = st.text_input("room", "Lab-101")
    with c3:
        temp_c = st.number_input("temp_c", value=23.0)
    with c4:
        rh_percent = st.number_input("rh_percent", value=45.0)
    with c5:
        co2_ppm = st.number_input("co2_ppm", value=700.0)
    with c6:
        lux = st.number_input("lux", value=500.0)

    if st.button("Insert test row"):
        try:
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "device_id": device_id,
                "room": room,
                "temp_c": float(temp_c),
                "rh_percent": float(rh_percent),
                "co2_ppm": float(co2_ppm),
                "lux": float(lux),
                "sensor_type": "manual_test",
            }

            supabase.table(SENSORS_TABLE).insert(payload).execute()
            st.success("Row inserted ✅")
            st.cache_data.clear()
            st.rerun()

        except APIError as e:
            st.error(
                f"Insert failed → code={getattr(e, 'code', None)} | "
                f"message={getattr(e, 'message', e)} | details={getattr(e, 'details', None)}"
            )
        except Exception as e:
            st.error(f"Insert failed: {e}")

# -------------------- end file --------------------
