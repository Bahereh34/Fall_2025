# ------------------------------- app.py --------------------------------
import io
import uuid
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Dict, List, Tuple

import streamlit as st
from supabase import create_client, Client

# 1) Page config — MUST be the first Streamlit command
st.set_page_config(page_title="Comfort Feedback", page_icon="📝", layout="centered")

# 2) Secrets -> variables (strip whitespace; remove trailing '/')
SUPABASE_URL   = st.secrets["SUPABASE_URL"].strip().rstrip("/")
SUPABASE_KEY   = st.secrets["SUPABASE_KEY"].strip()
SUPABASE_BUCKET = st.secrets.get("SUPABASE_BUCKET", "voice-recordings")
FEEDBACK_TABLE  = st.secrets.get("SUPABASE_TABLE", "feedback")
TABLE = FEEDBACK_TABLE

# 3) Create a single Supabase client (cached)
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# 4) Connectivity probe (helps catch URL/key typos)
host = urlparse(SUPABASE_URL).hostname or ""
try:
    _ = socket.gethostbyname(host)                        # DNS resolve
    supabase.table(TABLE).select("id").limit(1).execute() # simple round-trip
except Exception as e:
    st.error(f"❌ Supabase probe failed: {e}")

# 5) Optional deps (graceful fallbacks)
try:
    from audio_recorder_streamlit import audio_recorder  # audio-recorder-streamlit
    HAS_AUDIOREC = True
except Exception:
    HAS_AUDIOREC = False

# ============================= UI helpers ==============================
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

def yes_no_matrix(title: str, questions: List[str], key_prefix: str) -> Dict[str, bool]:
    """Render a Yes/No matrix without a 'Code' column."""
    st.header(title)
    st.caption("Modeled on the ECRHS style (tick Yes/No).")
    h1, h2 = st.columns([4, 2])
    with h1: st.markdown("**Question**")
    with h2: st.markdown("**Response**")
    out = {}
    for idx, text in enumerate(questions, start=1):
        c1, c2 = st.columns([4, 2])
        with c1: st.markdown(text)
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
    """Render a 1–5 satisfaction matrix."""
    st.header(title)
    st.caption("Scale: 1 = very dissatisfied … 5 = very satisfied")
    h1, h2 = st.columns([4, 2])
    with h1: st.markdown("**Question**")
    with h2: st.markdown("**1–5**")
    out = {}
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
            out[f"{key_prefix}_{key}"] = int(score)
    st.markdown("---")
    return out

def who5_matrix(title: str = "Well-Being (WHO-5)"):
    """WHO-5 (0–5 per item), returns answers dict + raw sum + scaled score (0–100)."""
    st.header(title)
    st.caption("In the **last 2 weeks**, how often have you felt the following? 5=All of the time … 0=At no time")
    # Column headers
    hq, h5, h4, h3, h2, h1, h0 = st.columns([4,1,1,1,1,1,1])
    with hq: st.markdown("**Question**")
    for c, lab in zip([h5,h4,h3,h2,h1,h0],
                      ["**5**<br/>All of the time",
                       "**4**<br/>Most of the time",
                       "**3**<br/>More than half",
                       "**2**<br/>Less than half",
                       "**1**<br/>Some of the time",
                       "**0**<br/>At no time"]):
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
        c_q, c5, c4, c3, c2, c1, c0 = st.columns([4,1,1,1,1,1,1])
        with c_q: st.markdown(text)
        val = st.slider(f"{key}_slider", 0, 5, 3, label_visibility="collapsed")
        for v, col in zip([5,4,3,2,1,0],[c5,c4,c3,c2,c1,c0]):
            col.markdown("●" if val==v else "○")
        answers[key] = int(val)

    raw_sum = sum(answers.values())    # 0–25
    scaled = raw_sum * 4               # 0–100

    st.markdown("---")
    st.subheader("WHO-5 Score")
    st.write(f"Raw: **{raw_sum}/25**  ·  Scaled: **{scaled}/100**")
    tip = "✅ ≥ 50 suggests acceptable well-being."
    if scaled < 50:
        tip = "⚠️ < 50 suggests reduced well-being; consider follow-up."
    if scaled < 28:
        tip += " **< 28 is a common cut-off for possible depression screening.**"
    st.caption(tip)
    st.markdown("---")
    return answers, raw_sum, scaled

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
brightness     = st.radio("Brightness level:", ["Too dim","OK","Too bright"], horizontal=True)
glare_rating   = st.slider("Glare discomfort (1=no glare, 5=severe glare)", 1, 5, 2)
gradient_legend(["#000000 0%","#6b7280 50%","#fde047 100%"], ["Dark","OK","Too bright"])
chip(glare_color(glare_rating), f"Glare = {glare_rating}", "👀")
task_affected  = st.checkbox("Glare/brightness is affecting my task (screen/board/paper)")
visual_notes   = st.text_area("Visual notes (optional):", placeholder="e.g., glare on screen; board is hard to read…")
st.markdown("---")

# ----------------------------- 3) Feeling / Concentration -----------------------------
st.header("3) Feeling / Concentration")
mood = st.selectbox("How do you feel right now?", ["Happy","Content/Neutral","Tired","Stressed/Anxious","Irritated","Other"])
mood_other = st.text_input("Please specify your feeling:") if mood == "Other" else ""
concentration = st.slider("How focused were you during the last 10 minutes?", 0, 10, 5,
                          help="0 = Not focused at all · 10 = Extremely focused")
productivity  = st.slider("How productive do you feel right now?", 0, 10, 5,
                          help="0 = Not productive · 10 = Extremely productive")
feeling_notes = st.text_area("Tell us a bit more (optional):", placeholder="e.g., Feeling distracted by temperature or lighting...")
st.markdown("---")

# ----------------------------- 4) Sleepiness / Fatigue (KSS) -----------------------------
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

# ----------------------------- 5) Clothing & Activity (PMV inputs) -----------------------------
st.header("5) What are you wearing and doing?")

# ---- ASHRAE-based clo values ----
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
    "Tie or turtle-neck (+5%)": 0.00,  # handled as multiplier
}

def compute_clo(selected: list[str]) -> tuple[float, dict]:
    base, mult, details = 0.0, 1.0, {}
    for item in selected:
        if item == "Tie or turtle-neck (+5%)":
            mult = 1.05
            details[item] = "+5%"
        else:
            v = CLO_ITEMS[item]
            base += v
            details[item] = v
    return round(base * mult, 2), details

tab_quick, tab_items = st.tabs(["Quick preset (like picture)", "Itemized garments (table)"])

with tab_quick:
    st.caption("Pick the outfit level that best matches the picture scale.")
    band = st.radio(
        "Outfit level",
        [
            "< 0.5 clo  (very light: shorts, T-shirt, sandals)",
            "0.6 – 1.2 clo  (typical indoor: trousers + shirt, light sweater)",
            "1.3 – 1.7 clo  (warmer outfit: sweater + jacket)",
            "1.8 – 2.4 clo  (coat, scarf, layered)",
            "2.5 – 3.4 clo  (heavy coat, hat, scarf)",
            "> 3.5 clo  (very heavy, outdoor winter)",
        ],
        index=1,
    )
    band_map = {
        "< 0.5 clo  (very light: shorts, T-shirt, sandals)": 0.45,
        "0.6 – 1.2 clo  (typical indoor: trousers + shirt, light sweater)": 0.90,
        "1.3 – 1.7 clo  (warmer outfit: sweater + jacket)": 1.50,
        "1.8 – 2.4 clo  (coat, scarf, layered)": 2.00,
        "2.5 – 3.4 clo  (heavy coat, hat, scarf)": 2.90,
        "> 3.5 clo  (very heavy, outdoor winter)": 3.60,
    }
    clo_quick = band_map[band]
    st.caption(f"Estimated clothing insulation (quick): **{clo_quick:.2f} clo**")

with tab_items:
    st.caption("Select what you are wearing now. The total clo is calculated from ASHRAE values.")
    colA, colB = st.columns(2)
    with colA:
        base_sel = st.multiselect(
            "Base & tops",
            [
                "Underwear (bra+panties/briefs)",
                "T-shirt / singlet",
                "Long underwear (upper)",
                "Shirt, short sleeve (light)",
                "Shirt, long sleeve (light)",
                "Shirt, long sleeve (heavy)",
                "Blouse, light",
                "Pullover, light",
                "Pullover, heavy (thick sweater)",
                "Vest, light",
                "Vest, heavy",
                "Tie or turtle-neck (+5%)",
            ],
        )
        leg_sel = st.multiselect(
            "Bottoms",
            [
                "Long underwear (lower)",
                "Trousers / slacks, light",
                "Trousers / slacks, heavy",
                "Skirt, light",
                "Skirt, heavy",
            ],
        )
    with colB:
        outer_sel = st.multiselect(
            "Outerwear",
            ["Jacket, light", "Jacket, heavy", "Coat (indoor short coat)"],
        )
        feet_sel = st.multiselect(
            "Socks & footwear",
            [
                "Socks, ankle length",
                "Socks, knee length",
                "Stockings / pantyhose",
                "Footwear: sandals",
                "Footwear: shoes",
                "Footwear: boots",
            ],
        )

    chosen_items = base_sel + leg_sel + outer_sel + feet_sel
    clo_itemized, clo_detail = compute_clo(chosen_items)
    st.caption(f"Estimated clothing insulation (itemized): **{clo_itemized:.2f} clo**")

clo_value = clo_itemized if chosen_items else clo_quick
chip_color = "#16a34a" if clo_value < 0.7 else ("#f59e0b" if clo_value < 1.4 else "#ef4444")
chip(chip_color, f"CLO = {clo_value:.2f}", "🧥")

st.subheader("Activity / Posture")
activity = st.selectbox(
    "What are you doing right now?",
    [
        "Seated, relaxed (≈1.0 met)",
        "Seated, working (≈1.2 met)",
        "Standing, light movement (≈1.4 met)",
        "Walking slowly (≈1.7 met)"
    ],
    index=1
)
activity_map = {
    "Seated, relaxed (≈1.0 met)": 1.0,
    "Seated, working (≈1.2 met)": 1.2,
    "Standing, light movement (≈1.4 met)": 1.4,
    "Walking slowly (≈1.7 met)": 1.7
}
met_value = activity_map[activity]
st.caption(f"Estimated metabolic rate: **{met_value:.1f} met**")
st.markdown("---")

# ----------------------------- 6) Symptoms (Yes/No) -----------------------------
symptom_questions = [
    "Have you had wheezing or whistling in your chest today?",
    "Have you felt short of breath while sitting or working indoors?",
    "Have you coughed during your time in this room?",
    "Have you had a blocked or runny nose indoors?",
    "Have you experienced itchy or watery eyes while indoors?",
    "Have you felt your throat was dry or irritated?",
    "Have you noticed any musty or damp smell?",
    "Have you had a headache while in this space?",
    "Have you felt unusually warm or cold in this space?",
    "Have you felt your concentration or mood was affected by the indoor environment?",
]
symptoms = yes_no_matrix("6) Symptoms", symptom_questions, key_prefix="symptom")
symptom_notes = st.text_area("Symptoms notes (optional)", placeholder="Anything to add about symptoms?")
st.markdown("---")

# ----------------------------- 7) Satisfaction (1–5) -----------------------------
satisfaction_questions = [
    ("overall",   "How satisfied are you with the overall indoor environment of the classroom/studio?"),
    ("privacy",   "How satisfied are you with the level of privacy during class or studio work?"),
    ("layout",    "How satisfied are you with the layout and spatial organization of the classroom/studio?"),
    ("appearance","How satisfied are you with the color, decoration, or visual appearance of the space?"),
    ("airmove",   "How satisfied are you with the air movement or ventilation in the space?"),
    ("clean",     "How satisfied are you with the cleanliness and hygiene of the environment?"),
    ("view",      "How satisfied are you with the outdoor view or visual connection to the outside environment?"),
]
satisfaction = likert_matrix("7) Satisfaction with the Space (1–5)", satisfaction_questions, key_prefix="sat")
satisfaction_notes = st.text_area("Satisfaction notes (optional)", placeholder="Anything to add about comfort, satisfaction, or space quality?")
st.markdown("---")

# ----------------------------- 8) WHO-5 Well-Being -----------------------------
who_answers, who_raw, who_scaled = who5_matrix()

# ----------------------------- Mini dashboard -----------------------------
st.subheader("Now")
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
with mc1: metric_card("KSS (sleepiness)", f"{kss_score}", "1 alert → 9 very sleepy", "🛌")
with mc2: metric_card("CLO", f"{clo_value:.2f}", "clothing insulation", "🧥")
with mc3: metric_card("Activity", f"{met_value:.1f} met", "metabolic rate", "🏃")
with mc4: metric_card("WHO-5", f"{who_scaled}", "0–100, ≥50 good", "🙂")
with mc5: metric_card("Room", room or "—", "location tag", "📍")
st.markdown("---")

# ----------------------------- 9) Optional Voice Note -----------------------------
st.header("9) Optional Voice Note")
st.caption("Click once to start, click again to stop (≤15 s). If mic is blocked, allow it in the browser’s site settings.")
audio_bytes = None
audio_mime = "audio/wav"
audio_seconds = None
voice_transcript = None

if HAS_AUDIOREC:
    raw = audio_recorder(text="Click to record / stop", recording_color="#ef4444",
                         neutral_color="#e5e7eb", icon_size="2x", key="voice_recorder_a")
    if raw:
        audio_bytes = raw
        st.audio(io.BytesIO(audio_bytes), format=audio_mime)
        st.success("Recorded! (If needed, click Reset form above before submitting.)")
else:
    st.info("Microphone recorder unavailable on this device. You can upload a short audio file instead.")
    upload = st.file_uploader("Upload voice note (≤15s; wav/mp3/m4a)", type=["wav", "mp3", "m4a"])
    if upload is not None:
        audio_bytes = upload.read()
        audio_mime = upload.type or "audio/wav"
        st.audio(io.BytesIO(audio_bytes), format=audio_mime)

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

            # Thermal / Visual / Feeling
            "thermal_sensation": thermal_sensation,
            "thermal_preference": thermal_preference,
            "air_movement": air_movement,
            "thermal_notes": (thermal_notes.strip() or None),
            "brightness": brightness,
            "glare_rating": glare_rating,
            "task_affected": task_affected,
            "visual_notes": (visual_notes.strip() or None),
            "mood": (mood if mood != "Other" else (mood_other.strip() or None)),
            "concentration": concentration,
            "productivity": productivity,
            "feeling_notes": (feeling_notes.strip() or None),

            # KSS
            "kss_score": kss_score,

            # Clothing & Activity
            "clo_value": clo_value,
            "clothing_detail": (chosen_items if chosen_items else [band]),
            "clothing_detail_map": (clo_detail if chosen_items else {}),
            "met_value": met_value,

            # Symptoms / Satisfaction
            "symptom_notes": (symptom_notes.strip() or None),
            "satisfaction_notes": (satisfaction_notes.strip() or None),

            # WHO-5
            "who5_raw_sum": who_raw,
            "who5_scaled_0_100": who_scaled,
        }

        # Merge matrix answers
        payload.update(symptoms)      # symptom01..10 -> bool
        payload.update(satisfaction)  # sat_overall, sat_privacy, ...

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

# ---------------------------- end of file -----------------------------
