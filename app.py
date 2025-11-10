# ------------------------- app.py (clean start) -------------------------
import io
import uuid
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

import streamlit as st
from supabase import create_client, Client

# 1) Page config — MUST be the first Streamlit command
st.set_page_config(page_title="Comfort Feedback", page_icon="📝", layout="centered")

# 2) Secrets -> variables (strip whitespace; remove trailing '/')
SUPABASE_URL  = st.secrets["SUPABASE_URL"].strip().rstrip("/")
SUPABASE_KEY  = st.secrets["SUPABASE_KEY"].strip()
SUPABASE_BUCKET = st.secrets.get("SUPABASE_BUCKET", "voice-recordings")
FEEDBACK_TABLE = st.secrets.get("SUPABASE_TABLE", "feedback")
SENSORS_TABLE  = st.secrets.get("SENSORS_TABLE", "sensor_readings")

#--------------------------------------


# (Use TABLE throughout the file for clarity)
TABLE = FEEDBACK_TABLE

# 3) Create a single Supabase client (cached)
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# 4) Connectivity probe (helps catch URL/key typos)
host = urlparse(SUPABASE_URL).hostname or ""
try:
    resolved_ip = socket.gethostbyname(host)        # DNS resolve
    supabase.table(TABLE).select("id").limit(1).execute()  # simple round-trip
    #st.caption(f"✅ Supabase connected ({host} → {resolved_ip})")
except Exception as e:
    st.error(f"❌ Supabase probe failed: {e}")

# 5) Optional deps (graceful fallbacks)
try:
    from audiorecorder import audiorecorder  # streamlit-audiorecorder
    HAS_AUDIOREC_B = True
except Exception:
    HAS_AUDIOREC_B = False

try:
    from audio_recorder_streamlit import audio_recorder  # audio-recorder-streamlit
    HAS_AUDIOREC_A = True
except Exception:
    HAS_AUDIOREC_A = False

try:
    import speech_recognition as sr
    HAS_SR = True
except Exception:
    HAS_SR = False

# ----------------------------- UI helpers -----------------------------
def gradient_legend(colors: list[str], labels: list[str], height: int = 10):
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

def thermal_color(v: int) -> str:
    return {-3:"#1e3a8a",-2:"#2563eb",-1:"#60a5fa",0:"#e5e7eb",1:"#fdba74",2:"#f97316",3:"#dc2626"}[int(v)]

def glare_color(v: int) -> str:
    return {1:"#000000",2:"#4b5563",3:"#9ca3af",4:"#f59e0b",5:"#fde047"}[int(v)]

def kss_color(score: int) -> str:
    return {1:"#16a34a",2:"#22c55e",3:"#4ade80",4:"#a3e635",5:"#eab308",6:"#f59e0b",7:"#fb923c",8:"#f97316",9:"#ef4444"}[int(score)]

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
        unsafe_allow_html=True
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
        unsafe_allow_html=True
    )

# ----------------------------- Title & meta -----------------------------
st.title("📝 Classroom Comfort Feedback")
col1, col2 = st.columns(2)
with col1:
    room = st.text_input("Room/Location (optional)")
with col2:
    user_id = st.text_input("User ID (optional)")
st.markdown("---")

# ----------------------------- 1) Thermal -----------------------------
st.header("1) Thermal Comfort")
thermal_sensation = st.slider(
    "Thermal sensation (ASHRAE 7-point)",
    min_value=-3, max_value=3, value=0,
    help="-3 Cold · -2 Cool · -1 Slightly Cool · 0 Neutral · +1 Slightly Warm · +2 Warm · +3 Hot",
)
gradient_legend(
    ["#1e3a8a 0%","#2563eb 16.6%","#60a5fa 33.3%","#e5e7eb 50%","#fdba74 66.6%","#f97316 83.3%","#dc2626 100%"],
    ["Cold","Cool","Slightly cool","Neutral","Slightly warm","Warm","Hot"]
)
chip(thermal_color(thermal_sensation), f"Thermal = {thermal_sensation}", "🌡️")
thermal_preference = st.radio("Do you want it…", ["No change","Warmer","Cooler"], horizontal=True)
air_movement = st.radio("Air movement feels…", ["Still","Slight breeze","Drafty"], horizontal=True)
thermal_notes = st.text_area("Thermal notes (optional):", placeholder="e.g., warm near window; stuffy air…")
st.markdown("---")

# ----------------------------- 2) Visual -----------------------------
st.header("2) Visual Comfort")
brightness = st.radio("Brightness level:", ["Too dim","OK","Too bright"], horizontal=True)
glare_rating = st.slider("Glare discomfort (1=no glare, 5=severe glare)", 1, 5, 2)
gradient_legend(["#000000 0%","#6b7280 50%","#fde047 100%"], ["Dark","OK","Too bright"])
chip(glare_color(glare_rating), f"Glare = {glare_rating}", "👀")
task_affected = st.checkbox("Glare/brightness is affecting my task (screen/board/paper)")
visual_notes = st.text_area("Visual notes (optional):", placeholder="e.g., glare on screen; board is hard to read…")
st.markdown("---")

# ----------------------------- 3) Feeling / Concentration -----------------------------
st.header("3) Feeling / Concentration")
mood = st.selectbox("How do you feel right now?", ["Happy","Content/Neutral","Tired","Stressed/Anxious","Irritated","Other"])
mood_other = st.text_input("Please specify your feeling:") if mood == "Other" else ""
concentration = st.slider("How focused were you during the last 10 minutes?", 0, 10, 5,
                          help="0 = Not focused at all · 10 = Extremely focused")
productivity = st.slider("How productive do you feel right now?", 0, 10, 5,
                         help="0 = Not productive · 10 = Extremely productive")
feeling_notes = st.text_area("Tell us a bit more (optional):", placeholder="e.g., Feeling distracted by temperature or lighting...")
st.markdown("---")

# ----------------------------- 4) KSS -----------------------------
st.header("4) Sleepiness / Fatigue (KSS)")
kss_options = [
    "1 – Extremely alert","2 – Very alert","3 – Alert","4 – Rather alert","5 – Neither alert nor sleepy",
    "6 – Some signs of sleepiness","7 – Sleepy, but no effort to stay awake",
    "8 – Sleepy, some effort to stay awake","9 – Very sleepy, great effort to stay awake, fighting sleep",
]
kss_label = st.radio("How sleepy do you feel right now?", kss_options, index=2)
kss_score = int(kss_label.split(" – ")[0])
gradient_legend(
    ["#16a34a 0%","#22c55e 12.5%","#4ade80 25%","#a3e635 37.5%","#eab308 50%","#f59e0b 62.5%","#fb923c 75%","#f97316 87.5%","#ef4444 100%"],
    ["1","2","3","4","5","6","7","8","9"]
)
chip(kss_color(kss_score), f"KSS = {kss_score}", "🛌")
st.markdown("---")

# ----------------------------- 5) Optional Physiology -----------------------------
with st.expander("🫀 Optional physiology (if wearing a device)"):
    colp1, colp2 = st.columns(2)
    with colp1:
        rmssd_ms = st.number_input("HRV (RMSSD, ms)", min_value=0.0, step=1.0,
                                   help="Enter resting RMSSD if available.")
    with colp2:
        skin_temp_c = st.number_input("Skin temperature (°C)", min_value=0.0, step=0.1,
                                      help="Wrist or skin thermistor.")
if "rmssd_ms" not in locals(): rmssd_ms = None
if "skin_temp_c" not in locals(): skin_temp_c = None

# ----------------------------- 6) Sensor snapshot -----------------------------
with st.expander("🔎 Light & Air snapshot (optional)"):
    coll1, coll2 = st.columns(2)
    with coll1:
        light_lux = st.number_input("Light level (lux)", min_value=0.0, step=1.0)
    with coll2:
        co2_ppm = st.number_input("CO₂ level (ppm)", min_value=0.0, step=50.0)
if "light_lux" not in locals(): light_lux = None
if "co2_ppm" not in locals(): co2_ppm = None
st.markdown("---")

# ----------------------------- Mini dashboard -----------------------------
st.subheader("Now")
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
with mc1: metric_card("KSS (sleepiness)", f"{kss_score}", "1 alert → 9 very sleepy", "🛌")
with mc2: metric_card("HRV (RMSSD)", f"{rmssd_ms if rmssd_ms else '—'} ms", "higher often → calmer", "🫀")
with mc3: metric_card("Skin Temp", f"{skin_temp_c if skin_temp_c else '—'} °C", "wrist/proximal", "🌡️")
with mc4: metric_card("Light", f"{light_lux if light_lux else '—'} lux", "task plane", "💡")
with mc5: metric_card("CO₂", f"{co2_ppm if co2_ppm else '—'} ppm", "ventilation proxy", "🫧")
st.markdown("---")

# ----------------------------- 7) Clothing -----------------------------
st.header("5) What are you wearing?")
clothing_choice = st.selectbox("Select your main clothing layer:", ["T-shirt","Sweater","Jacket","Coat","Other"])
clothing_other  = st.text_input("Please specify:") if clothing_choice == "Other" else ""
clothing_val = clothing_choice if clothing_choice != "Other" else (clothing_other.strip() or None)
st.markdown("---")
# ----------------------------- MATRIX HELPERS -----------------------------
from typing import Dict, List, Tuple

def yes_no_matrix(title: str, questions: List[Tuple[str, str]], key_prefix: str) -> Dict[str, bool]:
    """Render a Yes/No matrix; returns dict like {'q1_wheezing': True, ...}"""
    st.header(title)
    st.caption("Modeled on the ECRHS style (tick Yes/No).")

    # header row
    h1, h2, h3 = st.columns([0.5, 4, 2])
    with h1: st.markdown("**Code**")
    with h2: st.markdown("**Question**")
    with h3: st.markdown("**Response**")

    results = {}
    for idx, (code, text) in enumerate(questions, start=1):
        c1, c2, c3 = st.columns([0.5, 4, 2])
        with c1: st.markdown(code)
        with c2: st.markdown(text)
        with c3:
            v = st.radio(
                label=f"{key_prefix}_{idx}",
                options=["Yes", "No"],
                index=1,
                horizontal=True,
                label_visibility="collapsed",
                key=f"{key_prefix}_r{idx}",
            )
            results[f"{key_prefix}{idx:02d}"] = (v == "Yes")
    st.markdown("---")
    return results


def likert_matrix(title: str, questions: List[Tuple[str, str]], key_prefix: str) -> Dict[str, int]:
    """Render a 1–5 satisfaction matrix; returns dict like {'sat_overall': 4, ...}"""
    st.header(title)
    st.caption("Scale: 1 = very dissatisfied … 5 = very satisfied")

    # header row
    h1, h2 = st.columns([4, 2])
    with h1: st.markdown("**Question**")
    with h2: st.markdown("**1–5**")

    results = {}
    for key, text in questions:
        c1, c2 = st.columns([4, 2])
        with c1: st.markdown(text)
        with c2:
            score = st.slider(
                label=f"{key_prefix}_{key}",
                min_value=1, max_value=5, value=3,
                label_visibility="collapsed",
                key=f"{key_prefix}_{key}_slider",
            )
            results[f"{key_prefix}_{key}"] = int(score)
    st.markdown("---")
    return results
# ----------------------------- 3a) SYMPTOMS: Yes / No -----------------------------
symptom_questions = [
    ("Q1", "Have you had wheezing or whistling in your chest today?"),
    ("Q2", "Have you felt short of breath while sitting or working indoors?"),
    ("Q3", "Have you coughed during your time in this room?"),
    ("Q4", "Have you had a blocked or runny nose indoors?"),
    ("Q5", "Have you experienced itchy or watery eyes while indoors?"),
    ("Q6", "Have you felt your throat was dry or irritated?"),
    ("Q7", "Have you noticed any musty or damp smell?"),
    ("Q8", "Have you had a headache while in this space?"),
    ("Q9", "Have you felt unusually warm or cold in this space?"),
    ("Q10","Have you felt your concentration or mood was affected by the indoor environment?"),
]
symptoms = yes_no_matrix("6) Symptoms", symptom_questions, key_prefix="symptom")

# optional notes field for this block
symptom_notes = st.text_area("Symptoms notes (optional)", placeholder="Anything to add about symptoms?")

# ----------------------------- 3b) SATISFACTION: 1–5 -----------------------------
satisfaction_questions = [
    ("overall", "How satisfied are you with the overall indoor environment of the classroom/studio?"),
    ("privacy", "How satisfied are you with the level of privacy during class or studio work?"),
    ("layout", "How satisfied are you with the layout and spatial organization of the classroom/studio?"),
    ("appearance", "How satisfied are you with the color, decoration, or visual appearance of the space?"),
    ("airmove", "How satisfied are you with the air movement or ventilation in the space?"),
    ("clean", "How satisfied are you with the cleanliness and hygiene of the environment?"),
    ("view", "How satisfied are you with the outdoor view or visual connection to the outside environment?"),
]
satisfaction = likert_matrix("7) Satisfaction with the Space (1–5)", satisfaction_questions, key_prefix="sat")
st.markdown("---")
# ----------------------------- 8) Optional Voice Note -----------------------------
# ---- Voice Note (single component, clear UX) ----
import io, time

st.header("6) Optional Voice Note")
st.caption("Click once to start, click again to stop (≤15 s). If mic is blocked, allow it in the browser’s site settings.")

audio_bytes = None
audio_mime = "audio/wav"
audio_seconds = None          # <-- add this line
voice_transcript = None

try:
    from audio_recorder_streamlit import audio_recorder  # package: audio-recorder-streamlit

    # Show recorder
    st.write("**Recorder:**")
    raw = audio_recorder(
        text="Click to record / stop",
        recording_color="#ef4444",
        neutral_color="#e5e7eb",
        icon_size="2x",
        key="voice_recorder_a",
    )

    # Note: this component returns bytes **only after you stop** (click again).
    # You don't press-and-hold; it's click-to-toggle.
    if raw:
        audio_bytes = raw
        st.audio(io.BytesIO(audio_bytes), format=audio_mime)
        st.success("Recorded! (If you need, click Reset form above before submitting.)")

except Exception as e:
    st.info("Microphone recorder unavailable on this device. You can upload a short audio file instead.")
    upload = st.file_uploader("Upload voice note (≤15s; wav/mp3/m4a)", type=["wav", "mp3", "m4a"])
    if upload is not None:
        audio_bytes = upload.read()
        audio_mime = upload.type or "audio/wav"
        st.audio(io.BytesIO(audio_bytes), format=audio_mime)

# Optional manual summary
voice_note_text = st.text_input("Short summary (optional)", placeholder="e.g., tired; cold draft near window; glare on projector")

# ----------------------------- Submit / Reset -----------------------------
a1, a2 = st.columns([1, 2])
with a1:
    if st.button("Reset form"):
        st.rerun()

with a2:
    if st.button("Submit Feedback", type="primary"):
        payload = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "room": (room or None),
            "user_id": (user_id or None),
            # thermal
            "thermal_sensation": thermal_sensation,
            "thermal_preference": thermal_preference,
            "air_movement": air_movement,
            "thermal_notes": (thermal_notes.strip() or None),
            # visual
            "brightness": brightness,
            "glare_rating": glare_rating,
            "task_affected": task_affected,
            "visual_notes": (visual_notes.strip() or None),
            # feeling
            "mood": (mood if mood != "Other" else (mood_other.strip() or None)),
            "concentration": concentration,
            "productivity": productivity,
            "feeling_notes": (feeling_notes.strip() or None),
            # KSS / physiology / sensors
            "kss_score": kss_score,
            "rmssd_ms": (float(rmssd_ms) if rmssd_ms else None),
            "skin_temp_c": (float(skin_temp_c) if skin_temp_c else None),
            "light_lux": (float(light_lux) if light_lux else None),
            "co2_ppm": (float(co2_ppm) if co2_ppm else None),
            # clothing
            "clothing": clothing_val,
        }

        # Upload audio (private bucket)
        audio_path = None
        if audio_bytes:
            try:
                fname = f"voice/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}.wav"
                supabase.storage.from_(SUPABASE_BUCKET).upload(
                    path=fname, file=audio_bytes,
                    file_options={"content-type": audio_mime, "x-upsert": "true"},
                )
                audio_path = fname
            except Exception as e:
                st.error(f"⚠️ Audio upload failed: {e}")

        payload.update({
            "audio_path": audio_path,
            "audio_mime": (audio_mime if audio_path else None),
            "audio_seconds": (audio_seconds or None),
            "voice_transcript": (voice_transcript or None),
            "voice_note_text": (voice_note_text.strip() or None),
        })

        try:
            supabase.table(TABLE).insert(payload).execute()
            st.success("✅ Thanks! Your feedback was submitted.")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to submit: {e}")
# ------------------------- end file -------------------------








