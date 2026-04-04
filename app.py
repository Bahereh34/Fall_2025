# ------------------------------- app.py --------------------------------
import os
import io
import uuid
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Dict, List, Tuple
from pathlib import Path

import streamlit as st
from PIL import Image
from supabase import create_client, Client
from ui_helpers import yes_no_matrix, likert_matrix, who5_matrix
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

# ---------- CLO assets ----------
CLO_IMAGES = {
    "<0.5 clo": str(BASE_DIR / "assets" / "clo_images" / "1.jpg"),
    "0.6–1.2 clo": str(BASE_DIR / "assets" / "clo_images" / "2.jpg"),
    "1.3–1.7 clo": str(BASE_DIR / "assets" / "clo_images" / "3.jpg"),
    "1.8–2.4 clo": str(BASE_DIR / "assets" / "clo_images" / "4.jpg"),
    "2.5–3.4 clo": str(BASE_DIR / "assets" / "clo_images" / "5.jpg"),
    ">3.5 clo": str(BASE_DIR / "assets" / "clo_images" / "6.jpg"),
}

CLO_BANDS = [
    ("<0.5 clo", 0.45),
    ("0.6–1.2 clo", 0.90),
    ("1.3–1.7 clo", 1.50),
    ("1.8–2.4 clo", 2.10),
    ("2.5–3.4 clo", 2.95),
    (">3.5 clo", 3.50),
]

# ---------- Supabase ----------
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# quick connectivity probe
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

def yes_no_matrix(title: str, questions: List[str], key_prefix: str) -> Dict[str, bool]:
    st.header(title)
    st.caption("Modeled on the ECRHS style (tick Yes/No).")
    h1, h2 = st.columns([4, 2])
    with h1:
        st.markdown("**Question**")
    with h2:
        st.markdown("**Response**")

    out = {}
    for idx, text in enumerate(questions, start=1):
        c1, c2 = st.columns([4, 2])
        with c1:
            st.markdown(text)
        with c2:
            v = st.radio(
                label=f"{key_prefix}_{idx}",
                options=["Yes", "No"],
                index=1,
                horizontal=True,
                label_visibility="collapsed",
                key=f"{key_prefix}_r{idx}",
            )
            out[f"{key_prefix}{idx:02d}"] = (v == "Yes")

    st.markdown("---")
    return out

def likert_matrix(title: str, questions: List[Tuple[str, str]], key_prefix: str) -> Dict[str, int]:
    st.header(title)
    st.caption("Scale: 1 = very dissatisfied … 5 = very satisfied")
    h1, h2 = st.columns([4, 2])
    with h1:
        st.markdown("**Question**")
    with h2:
        st.markdown("**1–5**")

    out = {}
    for key, text in questions:
        c1, c2 = st.columns([4, 2])
        with c1:
            st.markdown(text)
        with c2:
            score = st.slider(
                label=f"{key_prefix}_{key}",
                min_value=1,
                max_value=5,
                value=3,
                label_visibility="collapsed",
                key=f"{key_prefix}_{key}_slider",
            )
            out[f"{key_prefix}_{key}"] = int(score)

    st.markdown("---")
    return out

def who5_matrix(title: str = "Well-Being (WHO-5)"):
    st.header(title)
    st.caption("In the last 2 weeks, how often have you felt the following? 5 = All of the time … 0 = At no time")

    hq, h5, h4, h3, h2, h1, h0 = st.columns([4, 1, 1, 1, 1, 1, 1])
    with hq:
        st.markdown("**Question**")
    for c, lab in zip(
        [h5, h4, h3, h2, h1, h0],
        [
            "**5**<br/>All of the time",
            "**4**<br/>Most of the time",
            "**3**<br/>More than half",
            "**2**<br/>Less than half",
            "**1**<br/>Some of the time",
            "**0**<br/>At no time",
        ],
    ):
        c.markdown(lab, unsafe_allow_html=True)

    items = [
        ("who1", "I have felt **cheerful and in good spirits**."),
        ("who2", "I have felt **calm and relaxed**."),
        ("who3", "I have felt **active and vigorous**."),
        ("who4", "I **woke up feeling fresh** and rested."),
        ("who5", "My **daily life** has been filled with **things that interest me**."),
    ]

    answers = {}
    for key, text in items:
        c_q, c5, c4, c3, c2, c1, c0 = st.columns([4, 1, 1, 1, 1, 1, 1])
        with c_q:
            st.markdown(text)
        val = st.slider(f"{key}_slider", 0, 5, 3, label_visibility="collapsed")
        for v, col in zip([5, 4, 3, 2, 1, 0], [c5, c4, c3, c2, c1, c0]):
            col.markdown("●" if val == v else "○")
        answers[key] = int(val)

    raw_sum = sum(answers.values())
    scaled = raw_sum * 4

    st.markdown("---")
    st.subheader("WHO-5 Score")
    st.write(f"Raw: **{raw_sum}/25**  ·  Scaled: **{scaled}/100**")

    tip = "✅ ≥ 50 suggests acceptable well-being."
    if scaled < 50:
        tip = "⚠️ < 50 suggests reduced well-being; consider follow-up."
    if scaled < 28:
        tip += " **< 28 is a common depression-screening cut-off.**"

    st.caption(tip)
    st.markdown("---")
    return answers, raw_sum, scaled

def pictogram_clo_picker(
    title: str,
    images: Dict[str, str],
    bands: List[Tuple[str, float]],
    state_key: str = "clo_band_sel",
) -> float:
    """Picture selector for clothing bands; returns clo value."""
    st.subheader(title)
    st.caption("Click the picture that best matches your outfit.")

    if state_key not in st.session_state:
        st.session_state[state_key] = bands[1][0]

    cols = st.columns(6, gap="small")
    for i, (band_key, _) in enumerate(bands):
        with cols[i]:
            path = images.get(band_key, "")
            if path and os.path.exists(path):
                try:
                    st.image(Image.open(path), use_column_width=True)
                except Exception:
                    st.markdown(
                        "<div style='height:140px;border:1px solid #eee;border-radius:12px;display:flex;align-items:center;justify-content:center;'>"
                        "<span style='opacity:.6'>[image]</span></div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    f"<div style='height:140px;border:1px solid #eee;border-radius:12px;display:flex;align-items:center;justify-content:center;background:#f8fafc;'>"
                    f"<span style='font-weight:600'>{band_key}</span></div>",
                    unsafe_allow_html=True,
                )

            chosen = st.button("Select", key=f"pick_{band_key}")
            st.caption(band_key)

            if chosen:
                st.session_state[state_key] = band_key

    band_to_value = {k: v for (k, v) in bands}
    selected_key = st.session_state[state_key]
    st.caption(f"Selected: **{selected_key}**")
    return float(band_to_value[selected_key])

# ---------- Clothing calculator ----------
CLO_ITEMS = {
    "Underwear (bra+panties/briefs)": 0.05,
    "T-shirt / singlet": 0.09,
    "Long underwear (upper)": 0.35,
    "Long underwear (lower)": 0.35,
    "Shirt, short sleeve (light)": 0.14,
    "Shirt, long sleeve (light)": 0.22,
    "Shirt, long sleeve (heavy)": 0.29,
    "Blouse, light": 0.20,
    "Dress, light": 0.22,
    "Dress, heavy": 0.70,
    "Vest, light": 0.15,
    "Vest, heavy": 0.29,
    "Skirt, light": 0.10,
    "Skirt, heavy": 0.22,
    "Trousers / slacks, light": 0.26,
    "Trousers / slacks, heavy": 0.32,
    "Pullover, light": 0.20,
    "Pullover, heavy (thick sweater)": 0.37,
    "Jacket, light": 0.22,
    "Jacket, heavy": 0.49,
    "Coat (indoor short coat)": 0.65,
    "Socks, ankle length": 0.04,
    "Socks, knee length": 0.10,
    "Stockings / pantyhose": 0.01,
    "Footwear: sandals": 0.02,
    "Footwear: shoes": 0.04,
    "Footwear: boots": 0.08,
    "Tie or turtle-neck (+5%)": 0.00,
}

def compute_clo(selected: List[str]) -> Tuple[float, Dict[str, object]]:
    base = 0.0
    mult = 1.0
    details = {}

    for item in selected:
        if item == "Tie or turtle-neck (+5%)":
            mult = 1.05
            details[item] = "+5%"
        else:
            v = CLO_ITEMS[item]
            base += v
            details[item] = v

    return round(base * mult, 2), details

# ---------- Title ----------
st.markdown("""
<div class="app-title">📝 Indoor Comfort Feedback Portal</div>
<div class="app-subtitle">
Share your thermal, visual, and well-being experience in this space.
</div>
""", unsafe_allow_html=True)
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Seat / Grid Location</div>', unsafe_allow_html=True)
st.markdown('<div class="section-caption">Please select the number that matches where you are sitting.</div>', unsafe_allow_html=True)

# ---------- Seat / Grid Location ----------
st.header("Grid Location")
st.caption("Please select the number that matches where you are sitting.")

GRID_IMAGE = str(BASE_DIR / "assets" / "clo_images" / "grid_numbered_plan.png")

if os.path.exists(GRID_IMAGE):
    st.image(Image.open(GRID_IMAGE), caption="Numbered seating/grid map", use_column_width=True)

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

st.markdown("---")
st.markdown('</div>', unsafe_allow_html=True)

# ---------- 1) Thermal ----------
st.header("1) Thermal")

st.subheader("A. Thermal sensation ")
st.caption("How do you feel right now?")

thermal_sensation = st.slider(
    "Thermal sensation",
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

st.subheader("B. Thermal comfort")
thermal_comfort = st.radio(
    "Are you comfortable?",
    ["Comfortable", "Slightly uncomfortable", "Uncomfortable"],
    horizontal=True,
)

st.subheader("C. Thermal preference")
thermal_preference = st.radio(
    "Would you prefer it to be:",
    ["Cooler", "No change", "Warmer"],
    horizontal=True,
)

# Keep this only if you still want extra thermal context
air_movement = st.radio(
    "Air movement feels…",
    ["Still", "Slight breeze", "Drafty"],
    horizontal=True,
)

thermal_notes = st.text_area(
    "Thermal notes (optional):",
    placeholder="e.g., warm near window; stuffy air; cold draft..."
)

st.markdown("---")

# ---------- 2) Visual ----------
st.header("2) Visual Comfort")

# A. Brightness perception
st.subheader("A. Brightness perception")
brightness = st.radio(
    "How is the light level at your current workspace?",
    ["Too dim", "Comfortable", "Too bright"],
    horizontal=True,
)

# B. Glare perception (CRITICAL)
st.subheader("B. Glare perception")
glare_level = st.radio(
    "Do you experience glare?",
    ["None", "Slight", "Moderate", "Severe"],
    horizontal=True,
)

# Optional visual cue (keep your nice UI logic)
glare_colors = {
    "None": "#16a34a",
    "Slight": "#84cc16",
    "Moderate": "#f59e0b",
    "Severe": "#ef4444",
}
chip(glare_colors[glare_level], f"Glare = {glare_level}", "👀")

# C. Visual comfort (evaluation)
st.subheader("C. Visual comfort")
visual_comfort = st.radio(
    "How comfortable is the lighting for your task?",
    ["Comfortable", "Slightly uncomfortable", "Uncomfortable"],
    horizontal=True,
)

# D. Task interference (IMPACT)
st.subheader("D. Task interference")
task_interference = st.radio(
    "Does the lighting affect your ability to work?",
    ["Yes", "No"],
    horizontal=True,
)

task_interference_note = None
if task_interference == "Yes":
    task_interference_note = st.text_area(
        "If yes, please explain:",
        placeholder="e.g., glare on screen, low light on desk, reflections..."
    )

visual_notes = st.text_area(
    "Additional visual notes (optional):",
    placeholder="Any other comments about lighting..."
)

st.markdown("---")

# ---------- Contextual Factors ----------
st.header("3) Contextual Factors")

# 1. Time
st.subheader("1. Time in this space")
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

# 2. Clothing (FULL CLO SECTION HERE)
st.subheader("2. Clothing (Thermal context)")
st.caption("Select your clothing level. You can use a quick estimate or a detailed selection.")

tab_quick, tab_scale, tab_items = st.tabs(
    ["Quick selection", "Continuous scale", "Detailed garments"]
)

clo_quick = 0.9
clo_cont = 0.9
clo_itemized = None
clo_detail = {}
chosen_items = []

# --- Quick (mapped to CLO) ---
with tab_quick:
    clothing_level = st.radio(
        "How would you describe your clothing?",
        ["Light", "Medium", "Heavy"],
        horizontal=True,
    )

    clothing_map = {
        "Light": 0.5,
        "Medium": 0.9,
        "Heavy": 1.3,
    }

    clo_quick = clothing_map[clothing_level]
    st.caption(f"Estimated: **{clo_quick:.2f} clo**")

# --- Continuous ---
with tab_scale:
    clo_cont = st.slider(
        "Clothing insulation (clo)",
        min_value=0.0,
        max_value=3.6,
        value=0.9,
        step=0.05,
    )
    st.caption(f"Selected: **{clo_cont:.2f} clo**")

# --- Detailed ---
with tab_items:
    st.caption("Select what you are wearing.")

    chosen_items = st.multiselect(
        "Garments",
        list(CLO_ITEMS.keys())
    )

    if chosen_items:
        clo_itemized, clo_detail = compute_clo(chosen_items)
        st.caption(f"Estimated: **{clo_itemized:.2f} clo**")

# --- Final CLO selection logic ---
if clo_itemized is not None:
    clo_value = clo_itemized
elif clo_cont is not None:
    clo_value = clo_cont
else:
    clo_value = clo_quick

chip(
    "#16a34a" if clo_value < 0.7 else ("#f59e0b" if clo_value < 1.4 else "#ef4444"),
    f"CLO = {clo_value:.2f}",
    "🧥",
)

# 3. Activity
st.subheader("3. Activity")
activity_type = st.selectbox(
    "What are you mainly doing right now?",
    [
        "Focused work (laptop / writing)",
        "Studio work (drawing / modeling)",
        "Discussion / group work",
        "Passive (listening / lecture)",
        "Other",
    ]
)

activity_other = ""
if activity_type == "Other":
    activity_other = st.text_input("Please specify activity")

st.markdown("---")
# ---------- 4) Impact on Work & Well-being ----------
st.header("4) Impact on Work & Well-being")

# A. Concentration
st.subheader("A. Concentration")
concentration = st.slider(
    "How well can you concentrate right now?",
    min_value=0,
    max_value=10,
    value=5,
    help="0 = Very poorly · 10 = Very well",
)

gradient_legend(
    ["#ef4444 0%", "#f59e0b 50%", "#16a34a 100%"],
    ["Very poorly", "Moderate", "Very well"]
)

chip(
    "#16a34a" if concentration >= 7 else ("#f59e0b" if concentration >= 4 else "#ef4444"),
    f"Concentration = {concentration}",
    "🧠",
)

# B. Productivity
st.subheader("B. Productivity")
productivity = st.slider(
    "How would you rate your productivity in this environment?",
    min_value=0,
    max_value=10,
    value=5,
    help="0 = Very low · 10 = Very high",
)

chip(
    "#16a34a" if productivity >= 7 else ("#f59e0b" if productivity >= 4 else "#ef4444"),
    f"Productivity = {productivity}",
    "📈",
)

# C. Mood
st.subheader("C. Mood")
mood = st.radio(
    "How does the environment affect your mood?",
    ["Positive", "Neutral", "Negative"],
    horizontal=True,
)

mood_colors = {
    "Positive": "#16a34a",
    "Neutral": "#9ca3af",
    "Negative": "#ef4444",
}

chip(mood_colors[mood], f"Mood = {mood}", "🙂")

# D. Fatigue / Sleepiness (KSS)
st.subheader("D. Fatigue / Sleepiness")

kss_opts = [
    "1 – Extremely alert",
    "2 – Very alert",
    "3 – Alert",
    "4 – Rather alert",
    "5 – Neither alert nor sleepy",
    "6 – Some signs of sleepiness",
    "7 – Sleepy, but no effort to stay awake",
    "8 – Sleepy, some effort to stay awake",
    "9 – Very sleepy, fighting sleep",
]

kss_label = st.radio("How sleepy do you feel right now?", kss_opts, index=2)
kss_score = int(kss_label.split(" – ")[0])

chip(
    {1: "#16a34a", 2: "#22c55e", 3: "#4ade80", 4: "#a3e635",
     5: "#eab308", 6: "#f59e0b", 7: "#fb923c", 8: "#f97316", 9: "#ef4444"}[kss_score],
    f"KSS = {kss_score}",
    "🛌",
)

st.markdown("---")


# ---------- Mini-cards ----------
st.subheader("Now")
mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)

with mc1:
    metric_card("Thermal", f"{thermal_sensation}", thermal_sensation_labels[thermal_sensation], "🌡️")
with mc2:
    metric_card("Comfort", thermal_comfort, "thermal comfort", "🙂")
with mc3:
    metric_card("KSS", f"{kss_score}", "1 alert → 9 sleepy", "🛌")
with mc4:
    metric_card("CLO", f"{clo_value:.2f}", "clothing insulation", "🧥")
with mc5:
    metric_card("Activity", f"{met_value:.1f} met", "metabolic rate", "🏃")
with mc6:
    metric_card("WHO-5", f"{who_scaled}", "0–100", "📊")

st.markdown("---")

# ---------- 9) Optional Voice Note ----------
st.header("9) Optional Voice Note")
st.caption("You can either record directly or upload a short audio file.")

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
    else:
        st.caption("No live recording captured yet.")

st.subheader("Or upload an audio file")
upload = st.file_uploader("Upload voice note (wav/mp3/m4a)", type=["wav", "mp3", "m4a"])

if upload is not None:
    audio_bytes = upload.read()
    audio_mime = upload.type or "audio/wav"
    st.success(f"Uploaded file: {len(audio_bytes)} bytes")
    st.audio(io.BytesIO(audio_bytes), format=audio_mime)

voice_note_text = st.text_input(
    "Short summary (optional)",
    placeholder="e.g., tired; cold draft near window; glare on projector",
)

# ---------- Submit / Reset ----------
left, right = st.columns([1, 2])

with left:
    if st.button("Reset form"):
        st.rerun()

with right:
    if st.button("Submit Feedback", type="primary"):
        # ---------- Derived variables ----------
        visual_discomfort_flag = (
        visual_comfort != "Comfortable"
        or glare_level in ["Moderate", "Severe"]
)
        payload = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "room": room or None,
            "user_id": user_id or None,

            # thermal / visual / feeling
            "thermal_sensation": thermal_sensation,
            "thermal_sensation_label": thermal_sensation_labels[thermal_sensation],
            "thermal_comfort": thermal_comfort,
            "thermal_preference": thermal_preference,
            "air_movement": air_movement,
            "thermal_notes": thermal_notes.strip() or None,
            "brightness": brightness,
            "glare_level": glare_level,
            "visual_comfort": visual_comfort,
            "task_interference": task_interference == "Yes",
            "task_interference_note": task_interference_note.strip() if task_interference_note else None,
            "visual_notes": visual_notes.strip() or None,
            "visual_discomfort_flag": visual_discomfort_flag,
            # contextual
            "time_in_space": time_in_space,
            "clothing_level_simple": clothing_level,
            "activity_type": activity_type if activity_type != "Other" else activity_other,
            "mood": mood if mood != "Other" else (mood_other.strip() or None),
            "concentration": concentration,
            "productivity": productivity,
            "feeling_notes": feeling_notes.strip() or None,
            "grid_number": int(grid_number),

            # KSS
            "kss_score": kss_score,

            # smartwatch
            "uses_smartwatch": uses_smartwatch,
            "watch_brand": watch_brand if uses_smartwatch else None,
            "heart_rate": heart_rate if uses_smartwatch else None,
            "hrv_ms": hrv_ms if uses_smartwatch and hrv_ms and hrv_ms > 0 else None,
            "stress_level": stress_level if uses_smartwatch else None,
            "wrist_temp_delta": wrist_temp_delta if uses_smartwatch else None,
            "sleep_hours": sleep_hours if uses_smartwatch else None,

            # clothing & activity


            "clo_value": clo_value,
            "clothing_detail": chosen_items if chosen_items else [],
            "clothing_detail_map": clo_detail if chosen_items else {},
            "time_in_space": time_in_space,
            "activity_type": activity_type if activity_type != "Other" else activity_other,

            # symptoms / satisfaction
            "symptom_notes": symptom_notes.strip() or None,
            "satisfaction_notes": satisfaction_notes.strip() or None,

            # WHO-5
            "who5_raw_sum": who_raw,
            "who5_scaled_0_100": who_scaled,
        }

        payload.update(symptoms)
        payload.update(satisfaction)
        payload.update(who_answers)

        # audio upload
        audio_path = None
        if audio_bytes:
            try:
                fname = f"voice/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}.wav"

                result = supabase.storage.from_(SUPABASE_BUCKET).upload(
                    path=fname,
                    file=audio_bytes,
                    file_options={"content-type": audio_mime, "x-upsert": "true"},
                )

                st.write("Upload result:", result)
                audio_path = fname
                st.success(f"Audio uploaded to: {audio_path}")

            except Exception as e:
                st.error(f"⚠️ Audio upload failed: {e}")
        else:
            st.warning("No audio bytes found, so nothing was uploaded.")

        payload.update(
            {
                "audio_path": audio_path,
                "audio_mime": audio_mime if audio_path else None,
                "audio_seconds": audio_seconds or None,
                "voice_transcript": voice_transcript or None,
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









