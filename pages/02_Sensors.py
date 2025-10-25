# pages/02_Sensors.py
from __future__ import annotations

import pandas as pd
import streamlit as st
from datetime import datetime, timezone
from supabase import create_client, Client
from postgrest import APIError

from supabase import create_client, Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
st.set_page_config(page_title="Comfort Dashboard", page_icon="📊", layout="wide")
st.title("📊 Comfort Dashboard")
try:
    supabase.table("feedback").select("id").limit(1).execute()
    st.caption("✅ Supabase connected")
except Exception as e:
    st.error(f"❌ Supabase probe failed: {e}")


# ---------- Page config ----------
st.set_page_config(page_title="Sensors Dashboard", page_icon="📟", layout="wide")
st.title("📟 Sensor Readings")

# ---------- Supabase client ----------
SUPABASE_URL: str = st.secrets["SUPABASE_URL"]
SUPABASE_KEY: str = st.secrets["SUPABASE_KEY"]          # service_role key recommended
SENSORS_TABLE: str = st.secrets.get("SENSORS_TABLE", "sensor_readings")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Optional quick probe so you can see if we can reach the table
def _probe_caption() -> None:
    try:
        probe = supabase.table(SENSORS_TABLE).select("id").limit(1).execute()
        total = "?" if getattr(probe, "count", None) is None else probe.count
        st.caption(f"Connected to Supabase · table='{SENSORS_TABLE}' · sample_rows={len(probe.data or [])}")
    except Exception as e:
        st.caption(f"Supabase probe failed: {e}")

_probe_caption()

# ---------- Data fetch (with good error messages) ----------
@st.cache_data(ttl=60)
def fetch_sensors(limit: int = 5000) -> pd.DataFrame:
    """
    Pull latest sensor rows. If anything fails, show the concrete API message
    and return an empty DataFrame (so the page doesn't crash).
    """
    try:
        res = (
            supabase.table(SENSORS_TABLE)
            .select("*")
            .order("ts", desc=True)         # expect a 'ts' timestamptz; we will fall back below
            .limit(limit)
            .execute()
        )
        data = res.data or []
    except APIError as e:
        st.error(
            f"Supabase error → code={getattr(e, 'code', None)} | "
            f"message={getattr(e, 'message', e)} | "
            f"details={getattr(e, 'details', None)} | "
            f"hint={getattr(e, 'hint', None)}"
        )
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Unexpected fetch error: {e}")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    if df.empty:
        return df

    # Normalize timestamp column
    tscol = "ts"
    if tscol not in df.columns:
        tscol = "timestamp" if "timestamp" in df.columns else None

    if tscol is None:
        st.warning("No 'ts' or 'timestamp' column found; showing un-timed data.")
        return df

    df[tscol] = pd.to_datetime(df[tscol], errors="coerce", utc=True)
    df = df.dropna(subset=[tscol]).rename(columns={tscol: "ts"}).sort_values("ts")
    return df


df = fetch_sensors()

# ---------- Empty state ----------
if df.empty:
    st.info("No sensor data yet. Use the insert tester below or your device to post readings.")
else:
    # ---------- Filters ----------
    top1, top2, top3 = st.columns(3)
    with top1:
        days_back = st.slider("Days back", min_value=1, max_value=30, value=7)
    with top2:
        devs = ["(all)"] + sorted(map(str, df.get("device_id", pd.Series(dtype=str)).dropna().unique()))
        dev_sel = st.selectbox("Device", devs)
    with top3:
        rooms = ["(all)"] + sorted(map(str, df.get("room", pd.Series(dtype=str)).dropna().unique()))
        room_sel = st.selectbox("Room", rooms)

    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days_back)

    mask = df["ts"] >= cutoff
    if dev_sel != "(all)":
        mask &= df.get("device_id", "") == dev_sel
    if room_sel != "(all)":
        mask &= df.get("room", "") == room_sel

    view = df.loc[mask].copy()

    # ---------- KPIs ----------
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Rows", int(len(view)))
    k2.metric("Devices", int(view.get("device_id", pd.Series(dtype=str)).nunique()))
    k3.metric("Avg CO₂ (ppm)", f"{view.get('co2_ppm', pd.Series(dtype=float)).dropna().mean():.0f}")
    k4.metric("Avg Lux", f"{view.get('lux', pd.Series(dtype=float)).dropna().mean():.0f}")

    # ---------- Charts ----------
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

    # ---------- Latest rows ----------
    st.subheader("Latest rows")
    st.dataframe(
        view.sort_values("ts", ascending=False).head(200),
        use_container_width=True,
        height=380,
    )

# ---------- Manual test insert ----------
with st.expander("Manual test insert (for debugging)"):
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        device_id = st.text_input("device_id", "esp32-classroom-01")
    with c2:
        room = st.text_input("room", "Lab-101")
    with c3:
        temp_c = st.number_input("temp_c", value=23.0)
    with c4:
        rh = st.number_input("rh", value=45.0)
    with c5:
        co2_ppm = st.number_input("co2_ppm", value=700)
    with c6:
        lux = st.number_input("lux", value=500)

    if st.button("Insert test row"):
        try:
            supabase.table(SENSORS_TABLE).insert(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "device_id": device_id,
                    "room": room,
                    "temp_c": float(temp_c),
                    "rh": float(rh),
                    "co2_ppm": float(co2_ppm),
                    "lux": float(lux),
                }
            ).execute()
            st.success("Row inserted ✅")
            st.cache_data.clear()
            st.rerun()
        except APIError as e:
            st.error(
                f"Insert failed → code={getattr(e, 'code', None)} | "
                f"message={getattr(e, 'message', e)} | "
                f"details={getattr(e, 'details', None)}"
            )
        except Exception as e:
            st.error(f"Insert failed: {e}")
