# ---- Top-of-file standard header (put this first) ----
import streamlit as st
from supabase import create_client, Client

# Read from Streamlit Secrets (must exist in Manage App → Secrets)
try:
    SUPABASE_URL: str = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY: str = st.secrets["SUPABASE_KEY"]
except KeyError as e:
    st.stop()  # show a clean error if secrets are missing
    # (Add SUPABASE_URL="https://<ref>.supabase.co" and SUPABASE_KEY="<anon key>" to secrets)

# Optional: other names you use elsewhere
BUCKET = st.secrets.get("SUPABASE_BUCKET", "voice-recordings")
FEEDBACK_TABLE = st.secrets.get("SUPABASE_TABLE", "feedback")
SENSORS_TABLE  = st.secrets.get("SENSORS_TABLE", "sensor_readings")

# Create one client (cache so each rerun reuses it)
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# (Streamlit requires this to be called early)
st.set_page_config(page_title="Comfort App", page_icon="📝", layout="wide")

# Quick connectivity probe (optional)
try:
    supabase.table(FEEDBACK_TABLE).select("id").limit(1).execute()
    st.caption("✅ Supabase connected")
except Exception as e:
    st.error(f"❌ Supabase probe failed: {e}")
    st.stop()
# ---- end standard header ----


# 04_Voice_Playback.py
from datetime import datetime
import streamlit as st
from supabase import create_client, Client


st.title("🎧 Playback")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BUCKET = st.secrets.get("SUPABASE_BUCKET", "voice-recordings")
TABLE = st.secrets.get("SUPABASE_TABLE", "feedback")
SIGNED_SECONDS = int(st.secrets.get("SIGNED_SECONDS", 3600))

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Filters
c1, c2 = st.columns(2)
room_filter = c1.text_input("Filter by room (optional)")
type_filter = c2.selectbox("Filter by type", ["", "thermal", "visual", "acoustic", "IAQ", "other"], index=0)

# Query rows with audio (audio_path IS NOT NULL)
q = (
    supabase.table(TABLE)
    .select("*")
    .not_.is_("audio_path", "null")   # <-- FIX
    .order("timestamp", desc=True)
)
if room_filter.strip():
    q = q.ilike("room", f"%{room_filter.strip()}%")
if type_filter:
    q = q.eq("feedback_type", type_filter)

res = q.execute()
rows = res.data or []

if not rows:
    st.info("No recordings yet.")
    st.stop()

for r in rows:
    ts = r.get("timestamp")
    dt = ts if isinstance(ts, str) else datetime.fromisoformat(ts)
    label = f"{dt} • {r.get('room') or '—'} • {r.get('feedback_type') or '—'}"
    with st.expander(label):
        st.write("Transcript:", r.get("feedback_text") or "—")
        path = r.get("audio_path")
        if path:
            # signed URL (works with private bucket + service_role key)
            try:
                signed = supabase.storage.from_(BUCKET).create_signed_url(path, SIGNED_SECONDS)
                st.audio(signed.get("signedURL"))
            except Exception as e:
                st.error(f"Could not create signed URL: {e}")
