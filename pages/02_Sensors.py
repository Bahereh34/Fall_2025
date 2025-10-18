import pandas as pd
import streamlit as st
from supabase import create_client, Client
from postgrest import APIError

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
SENSORS_TABLE = st.secrets.get("SENSORS_TABLE", "sensor_readings")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=30)
def fetch_sensors(limit=5000) -> pd.DataFrame:
    try:
        # minimal probe first
        probe = supabase.table(SENSORS_TABLE).select("id").limit(1).execute()
        # real query
        res = (supabase.table(SENSORS_TABLE)
               .select("*")
               .order("ts", desc=True)
               .limit(limit)
               .execute())
    except APIError as e:
        st.error(
            f"Supabase error → code={getattr(e, 'code', None)}, "
            f"msg={getattr(e, 'message', e)}, "
            f"details={getattr(e, 'details', None)}, "
            f"hint={getattr(e, 'hint', None)}"
        )
        return pd.DataFrame()

    df = pd.DataFrame(res.data or [])
    if df.empty:
        return df

    tscol = "ts" if "ts" in df.columns else ("timestamp" if "timestamp" in df.columns else None)
    if tscol is None:
        return df

    df[tscol] = pd.to_datetime(df[tscol], errors="coerce", utc=True)
    df = df.dropna(subset=[tscol]).rename(columns={tscol: "ts"}).sort_values("ts")
    return df
