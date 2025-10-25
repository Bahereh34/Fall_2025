# -------------------- pages/04_Voice_Playback.py (clean) --------------------
import socket
from urllib.parse import urlparse
from datetime import datetime

import streamlit as st
from supabase import Client, create_client

# 1) Page config — must be FIRST Streamlit call
st.set_page_config(page_title="Voice Playback", page_icon="🎧", layout="wide")
st.title("🎧 Playback")

# 2) Secrets → vars
SUPABASE_URL  = st.secrets["SUPABASE_URL"].strip().rstrip("/")
SUPABASE_KEY  = st.secrets["SUPABASE_KEY"].strip()
BUCKET        = st.secrets.get("SUPABASE_BUCKET", "voice-recordings")
TABLE         = st.secrets.get("SUPABASE_TABLE", "feedback")
SIGNED_SECONDS = int(st.secrets.get("SIGNED_SECONDS", 3600))

# 3) One Supabase client (cached)
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# 4) Connectivity probe
host = urlparse(SUPABASE_URL).hostname or ""
try:
    _ip = socket.gethostbyname(host)
    supabase.table(TABLE).select("id").limit(1).execute()
    st.caption(f"✅ Supabase connected ({host} → {_ip})")
except Exception as e:
    st.error(f"❌ Supabase probe failed: {e}")

# ---------- Filters ----------
c1, c2 = st.columns(2)
room_filter = c1.text_input("Filter by room (optional)")
type_filter = c2.selectbox(
    "Filter by type",
    ["(all)", "thermal", "visual", "acoustic", "IAQ", "other"],
    index=0,
)

# ---------- Query rows with audio ----------
q = (
    supabase.table(TABLE)
    .select("*")
    .not_.is_("audio_path", "null")   # rows where audio_path IS NOT NULL
    .order("timestamp", desc=True)
)
if room_filter.strip():
    q = q.ilike("room", f"%{room_filter.strip()}%")
if type_filter != "(all)":
    q = q.eq("feedback_type", type_filter)

res = q.execute()
rows = res.data or []

if not rows:
    st.info("No recordings yet.")
    st.stop()

# ---------- List items ----------
for r in rows:
    ts_raw = r.get("timestamp")
    try:
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if isinstance(ts_raw, str) else ts_raw
    except Exception:
        ts = ts_raw
    label = f"{ts} • {r.get('room') or '—'} • {r.get('feedback_type') or '—'}"

    with st.expander(label):
        st.write("Transcript:", r.get("feedback_text") or r.get("voice_transcript") or "—")
        path = r.get("audio_path")

        if path:
            # Prefer signed URL (private bucket with service/anon if policy allows)
            try:
                signed = supabase.storage.from_(BUCKET).create_signed_url(path, SIGNED_SECONDS)
                url = signed.get("signedURL")
                if not url:
                    # fall back to public URL if the bucket/object is public
                    url = supabase.storage.from_(BUCKET).get_public_url(path)
                st.audio(url)
            except Exception as e:
                # Fall back to public URL attempt + show error if that also fails
                try:
                    url = supabase.storage.from_(BUCKET).get_public_url(path)
                    st.audio(url)
                    st.caption("Used public URL (signed URL not available).")
                except Exception as e2:
                    st.error(f"Could not load audio: {e} / {e2}")
        else:
            st.caption("No audio_path stored for this row.")
# -------------------- end file --------------------
