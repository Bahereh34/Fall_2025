# ------------------------------- app.py --------------------------------
import os
import io
import uuid
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse
from pathlib import Path
from typing import List

import streamlit as st
from PIL import Image
from supabase import create_client, Client

# ---------- Page & Secrets ----------
st.set_page_config(page_title="Comfort Feedback", page_icon="📝", layout="centered")

SUPABASE_URL = st.secrets["SUPABASE_URL"].strip().rstrip("/")
SUPABASE_KEY = st.secrets["SUPABASE_KEY"].strip()
SUPABASE_BUCKET = st.secrets.get("SUPABASE_BUCKET", "voice-recordings")
FEEDBACK_TABLE = st.secrets.get("SUPABASE_TABLE", "feedback")
TABLE = FEEDBACK_TABLE

BASE_DIR = Path(__file__).resolve().parent

# ---------- Load custom CSS ----------
def load_css():
    css_path = BASE_DIR / "style.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# ---------- Supabase ----------
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

try:
    host = urlparse(SUPABASE_URL).hostname or ""
    _ = socket.gethostbyname(host)
    supabase.table(TABLE).select("id").limit(1).execute()
except Exception as e:
    st.error(f"❌ Supabase probe failed: {e}")

# ---------- Optional audio recorder ----------
try:
    from audio_recorder_streamlit import audio_recorder
    HAS_AUDIOREC = True
except Exception:
    HAS_AUDIOREC = False

# ---------- UI helpers ----------
def gradient_legend(colors: List[str], labels: List[str], height: int = 10):
    bar = f"linear-gradient(90deg, {', '.join(colors)})"
    ticks = "".join([f"<span>{lbl}</span>" for lbl in labels])
    st.markdown(
        f"""
        <div style="margin:6px 2px 2px 2px;">
          <div style="width:100%;height:{height}px;border-radius:8px;background:{bar};
                      box-shadow: inset 0 0 0 1px rgba(0,0,0,0.06);"></div>
          <div style="display:flex;justify-content:space-between;font-size:0.8rem;
                      opacity:0.75;margin-top:4px;">
            {ticks}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def chip(color: str, text: str, icon: str = "") -> None:
    st.markdown(
        f"""
        <div style="display:inline-flex;align-items:center;gap:8px;padding:8px 10px;margin:6px 0;
                    border-radius:999px;background:rgba(0,0,0,0.03);
                    border:1px solid rgba(0,0,0,0.05)">
          <span style="width:12px;height:12px;border-radius:50%;background:{color};
                       border:1px solid rgba(0,0,0,.1)"></span>
          <span style="font-size:.9rem;opacity:.85">{icon} {text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

def metric_card(title: str, value: str, sub: str = "", icon: str = ""):
    st.markdown(
        f"""
        <div style="border:1px solid rgba(0,0,0,0.06);border-radius:16px;padding:14px 16px;
                    background:white;box-shadow:0 1px 2px rgba(0,0,0,0.04);">
          <div style="font-size:.8rem;opacity:.7;margin-bottom:6px;">{icon} {title}</div>
          <div style="font-weight:700;font-size:1.2rem">{value}</div>
          <div style="font-size:.8rem;opacity:.6">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------- Title ----------
st.markdown("""
<div class="app-title">📝 Indoor Comfort Feedback Portal</div>
<div class="app-subtitle">
Share your thermal, visual, and work-related experience in this space.
</div>
""", unsafe_allow_html=True)

# ---------- Seat / Grid Location ----------
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Seat / Grid Location</div>', unsafe_allow_html=True)
st.markdown('<div class="section-caption">Please select the number that matches where you are sitting.</div>', unsafe_allow_html=True)

GRID_IMAGE = str(BASE_DIR / "assets" / "clo_images" / "grid_numbered_plan.png")
if os.path.exists(GRID_IMAGE):
    st.image(GRID_IMAGE, caption="Numbered seating/grid map", use_column_width=True)
else:
    st.warning("Grid image not found.")
grid_number = st.number_input(
    "Your seat/grid number",
    min_value=1,
    max_value=120,
    value=1,
    step=1
)

c1, c2 = st.columns(2)
with c1:
    room = st.text_input("Room/Location (optional)")
with c2:
    user_id = st.text_input("User ID (optional)")

st.markdown('</div>', unsafe_allow_html=True)
st.markdown("---")

# ---------- 1) Thermal Comfort ----------
st.header("1) Thermal Comfort")

thermal_sensation = st.slider(
    "How do you feel right now?",
    min_value=-3,
    max_value=3,
    value=0,
    help="-3 Cold · -2 Cool · -1 Slightly cool · 0 Neutral · +1 Slightly warm · +2 Warm · +3 Hot",
)

thermal_sensation_labels = {
    -3: "Cold",
    -2: "Cool",
    -1: "Slightly cool",
     0: "Neutral",
     1: "Slightly warm",
     2: "Warm",
     3: "Hot",
}

gradient_legend(
    ["#1e3a8a 0%", "#2563eb 16.6%", "#60a5fa 33.3%", "#e5e7eb 50%", "#fdba74 66.6%", "#f97316 83.3%", "#dc2626 100%"],
    ["Cold", "Cool", "Slightly cool", "Neutral", "Slightly warm", "Warm", "Hot"],
)

chip(
    {-3: "#1e3a8a", -2: "#2563eb", -1: "#60a5fa", 0: "#e5e7eb", 1: "#fdba74", 2: "#f97316", 3: "#dc2626"}[thermal_sensation],
    f"{thermal_sensation_labels[thermal_sensation]} ({thermal_sensation})",
    "🌡️",
)

thermal_comfort = st.radio(
    "Are you comfortable?",
    ["Comfortable", "Slightly uncomfortable", "Uncomfortable"],
    horizontal=True,
)

thermal_preference = st.radio(
    "Would you prefer it to be:",
    ["Cooler", "No change", "Warmer"],
    horizontal=True,
)

st.markdown("---")

# ---------- 2) Visual Comfort ----------
st.header("2) Visual Comfort")

brightness = st.radio(
    "How is the light level at your current workspace?",
    ["Too dim", "Comfortable", "Too bright"],
    horizontal=True,
)

glare_level = st.radio(
    "Do you experience glare?",
    ["None", "Slight", "Moderate", "Severe"],
    horizontal=True,
)

glare_colors = {
    "None": "#16a34a",
    "Slight": "#84cc16",
    "Moderate": "#f59e0b",
    "Severe": "#ef4444",
}
chip(glare_colors[glare_level], f"Glare = {glare_level}", "👀")

visual_comfort = st.radio(
    "How comfortable is the lighting for your task?",
    ["Comfortable", "Slightly uncomfortable", "Uncomfortable"],
    horizontal=True,
)

st.markdown("---")

# ---------- 3) Task Impact ----------
st.header("3) Task Impact")

task_interference = st.radio(
    "Does the environment affect your ability to work?",
    ["Yes", "No"],
    horizontal=True,
)

task_interference_note = None
if task_interference == "Yes":
    task_interference_note = st.text_area(
        "If yes, please explain:",
        placeholder="e.g., glare on screen, warm air, low light on desk..."
    )

concentration = st.slider(
    "How well can you concentrate right now?",
    min_value=0,
    max_value=10,
    value=5,
    help="0 = Very poorly · 10 = Very well",
)

productivity = st.slider(
    "How would you rate your productivity in this environment?",
    min_value=0,
    max_value=10,
    value=5,
    help="0 = Very low · 10 = Very high",
)

st.markdown("---")

# ---------- 4) Time in Space ----------
st.header("4) Time in Space")

time_in_space = st.radio(
    "How long have you been in this space?",
    [
        "Less than 15 minutes",
        "15–60 minutes",
        "1–3 hours",
        "More than 3 hours",
    ],
    horizontal=True,
)

st.markdown("---")

# ---------- Summary cards ----------
visual_discomfort_flag = (
    visual_comfort != "Comfortable"
    or glare_level in ["Moderate", "Severe"]
)

st.subheader("Now")
mc1, mc2, mc3, mc4, mc5 = st.columns(5)

with mc1:
    metric_card("Seat", str(grid_number), "grid number", "📍")
with mc2:
    metric_card("Thermal", f"{thermal_sensation}", thermal_sensation_labels[thermal_sensation], "🌡️")
with mc3:
    metric_card("Visual", visual_comfort, "lighting comfort", "👀")
with mc4:
    metric_card("Focus", f"{concentration}/10", "current concentration", "🧠")
with mc5:
    metric_card("Time", time_in_space, "duration in space", "⏱️")

st.markdown("---")


# ---------- 5) Open-ended Feedback ----------
st.header("5) Open-ended Feedback")
st.caption("You can briefly describe your experience in text and optionally record or upload a voice note.")

st.subheader("Brief description")
open_feedback_text = st.text_area(
    "Can you briefly describe your experience?",
    placeholder="Examples:\n• Sunlight is hitting my screen\n• It feels stuffy\n• Too bright near the window",
    height=120,
)

feedback_influence = st.radio(
    "Did others’ feedback influence your response?",
    ["Not at all", "Slightly", "Moderately", "Strongly"],
    horizontal=True,
)

st.markdown("---")

st.subheader("Voice note (optional)")
st.caption("You can record a short voice note or upload an audio file.")
st.header("5) Open-Ended Feedback")


audio_bytes = None
audio_mime = "audio/wav"
audio_seconds = None
voice_transcript = None

if HAS_AUDIOREC:
    st.subheader("Record directly")
    raw = audio_recorder(
        text="Click to record / stop",
        recording_color="#ef4444",
        neutral_color="#e5e7eb",
        icon_size="2x",
        key="voice_recorder_a",
    )

    if raw is not None:
        audio_bytes = raw
        st.success(f"Recorded successfully: {len(audio_bytes)} bytes")
        st.audio(io.BytesIO(audio_bytes), format=audio_mime)

st.subheader("Or upload an audio file")
upload = st.file_uploader("Upload voice note (wav/mp3/m4a)", type=["wav", "mp3", "m4a"])

if upload is not None:
    audio_bytes = upload.read()
    audio_mime = upload.type or "audio/wav"
    st.success(f"Uploaded file: {len(audio_bytes)} bytes")
    st.audio(io.BytesIO(audio_bytes), format=audio_mime)


# ---------- Submit / Reset ----------
left, right = st.columns([1, 2])

with left:
    if st.button("Reset form"):
        st.rerun()

with right:
    if st.button("Submit Feedback", type="primary"):
        payload = {
    "id": str(uuid.uuid4()),
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "room": room.strip() or None,
    "user_id": user_id.strip() or None,
    "grid_number": int(grid_number),

    "thermal_sensation": thermal_sensation,
    "thermal_sensation_label": thermal_sensation_labels[thermal_sensation],
    "thermal_comfort": thermal_comfort,
    "thermal_preference": thermal_preference,

    "brightness": brightness,
    "glare_level": glare_level,
    "visual_comfort": visual_comfort,
    "visual_discomfort_flag": visual_discomfort_flag,

    "task_interference": task_interference == "Yes",
    "task_interference_note": task_interference_note.strip() if task_interference_note else None,
    "concentration": concentration,
    "productivity": productivity,

    "time_in_space": time_in_space,

    "open_feedback_text": open_feedback_text.strip() or None,
    "feedback_influence": feedback_influence,
}
        # audio upload
        audio_path = None
        if audio_bytes:
            try:
                fname = f"voice/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}.wav"

                supabase.storage.from_(SUPABASE_BUCKET).upload(
                    path=fname,
                    file=audio_bytes,
                    file_options={"content-type": audio_mime, "x-upsert": "true"},
                )
                audio_path = fname
            except Exception as e:
                st.error(f"⚠️ Audio upload failed: {e}")

        payload.update(
            {
                "audio_path": audio_path,
                "audio_mime": audio_mime if audio_path else None,
                "audio_seconds": audio_seconds,
                "voice_transcript": voice_transcript,
                "voice_note_text": voice_note_text.strip() or None,
            }
        )

        try:
            supabase.table(TABLE).insert(payload).execute()
            st.success("✅ Thanks! Your feedback was submitted.")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to submit: {e}")

# ---------------------------- end of file ----------------------------
