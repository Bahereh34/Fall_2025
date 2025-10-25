import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import uuid

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="Comfort Feedback", page_icon="📝", layout="centered")

# -----------------------------
# UI helpers
# -----------------------------
def gradient_legend(colors: list[str], labels: list[str], height: int = 10):
    """Draw a horizontal gradient bar with evenly spaced labels underneath."""
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
    # -3..+3 → blue→red palette
    return {
        -3: "#1e3a8a", -2: "#2563eb", -1: "#60a5fa",
         0: "#e5e7eb",  1: "#fdba74",  2: "#f97316",  3: "#dc2626"
    }[int(v)]

def glare_color(v: int) -> str:
    # 1..5 → black→yellow
    return {1:"#000000", 2:"#4b5563", 3:"#9ca3af", 4:"#f59e0b", 5:"#fde047"}[int(v)]

def kss_color(score: int) -> str:
    # 1..9 (alert → sleepy): green → yellow → red
    scale = {
        1:"#16a34a", 2:"#22c55e", 3:"#4ade80",
        4:"#a3e635", 5:"#eab308",
        6:"#f59e0b", 7:"#fb923c", 8:"#f97316", 9:"#ef4444"
    }
    return scale[int(score)]

def chip(color: str, text: str, icon: str = "") -> str:
    return f"""
    <div style="display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:999px;
                background:rgba(0,0,0,0.03);border:1px solid rgba(0,0,0,0.05)">
      <span style="width:12px;height:12px;border-radius:50%;background:{color};
                   border:1px solid rgba(0,0,0,.1)"></span>
      <span style="font-size:.9rem;opacity:.85">{icon} {text}</span>
    </div>
    """

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

# -----------------------------
# Supabase (read from Streamlit secrets)
# -----------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# Title + meta fields
# -----------------------------
st.title("📝 Classroom Comfort Feedback")

col1, col2 = st.columns(2)
with col1:
    room = st.text_input("Room/Location (optional)")
with col2:
    user_id = st.text_input("User ID (optional)")

st.markdown("---")

# -----------------------------

# 2) Thermal Comfort
# -----------------------------
st.header("2) Thermal Comfort")
thermal_sensation = st.slider(
    "Thermal sensation (ASHRAE 7-point)",
    min_value=-3, max_value=3, value=0,
    help="-3 Cold · -2 Cool · -1 Slightly Cool · 0 Neutral · +1 Slightly Warm · +2 Warm · +3 Hot",
)

# Spectrum: cool → neutral → hot
thermal_colors = [
    "#1e3a8a 0%", "#2563eb 16.6%", "#60a5fa 33.3%",
    "#e5e7eb 50%", "#fdba74 66.6%", "#f97316 83.3%", "#dc2626 100%"
]
thermal_labels = ["Cold", "Cool", "Slightly cool", "Neutral", "Slightly warm", "Warm", "Hot"]
gradient_legend(thermal_colors, thermal_labels)

# Live color chip for thermal
st.markdown(
    chip(thermal_color(thermal_sensation), f"Thermal = {thermal_sensation}", "🌡️"),
    unsafe_allow_html=True,
)

thermal_preference = st.radio("Do you want it…", ["No change", "Warmer", "Cooler"], horizontal=True)
air_movement = st.radio("Air movement feels…", ["Still", "Slight breeze", "Drafty"], horizontal=True)
thermal_notes = st.text_area("Thermal notes (optional):", placeholder="e.g., warm near window; stuffy air…")

st.markdown("---")

# -----------------------------
# 3) Visual Comfort
# -----------------------------
st.header("3) Visual Comfort")
brightness = st.radio("Brightness level:", ["Too dim", "OK", "Too bright"], horizontal=True)
glare_rating = st.slider("Glare discomfort (1=no glare, 5=severe glare)", 1, 5, 2)

# Spectrum: dark → OK → bright
glare_colors = ["#000000 0%", "#6b7280 50%", "#fde047 100%"]
glare_labels = ["Dark", "OK", "Too bright"]
gradient_legend(glare_colors, glare_labels)

# Live color chip for glare
st.markdown(
    chip(glare_color(glare_rating), f"Glare = {glare_rating}", "👀"),
    unsafe_allow_html=True,
)

task_affected = st.checkbox("Glare/brightness is affecting my task (screen/board/paper)")
visual_notes = st.text_area("Visual notes (optional):", placeholder="e.g., glare on screen; board is hard to read…")

st.markdown("---")

# -----------------------------
# 1) Feeling
# -----------------------------
st.header("1) Feeling")
mood = st.selectbox(
    "How do you feel right now?",
    ["Happy", "Content/Neutral", "Tired", "Stressed/Anxious", "Irritated", "Other"],
)
mood_other = st.text_input("Please specify your feeling:") if mood == "Other" else ""
feeling_notes = st.text_area(
    "Tell us a bit more (optional):",
    placeholder="e.g., I’m a bit tired after lunch; noise is distracting…",
)

st.markdown("---")

# -----------------------------
# 4) Sleepiness / Fatigue (KSS)
# -----------------------------
st.header("4) Sleepiness / Fatigue (KSS)")

kss_options = [
    "1 – Extremely alert",
    "2 – Very alert",
    "3 – Alert",
    "4 – Rather alert",
    "5 – Neither alert nor sleepy",
    "6 – Some signs of sleepiness",
    "7 – Sleepy, but no effort to stay awake",
    "8 – Sleepy, some effort to stay awake",
    "9 – Very sleepy, great effort to stay awake, fighting sleep",
]
kss_label = st.radio("How sleepy do you feel right now?", kss_options, index=2)
kss_score = int(kss_label.split(" – ")[0])

# KSS gradient (green → yellow → red)
kss_colors = [
    "#16a34a 0%", "#22c55e 12.5%", "#4ade80 25%",
    "#a3e635 37.5%", "#eab308 50%",
    "#f59e0b 62.5%", "#fb923c 75%", "#f97316 87.5%", "#ef4444 100%"
]
kss_labels = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
gradient_legend(kss_colors, kss_labels)

st.markdown(
    chip(kss_color(kss_score), f"KSS = {kss_score}", "🛌"),
    unsafe_allow_html=True,
)

st.markdown("---")

# -----------------------------
# 5) Optional Physiology (HRV & Skin Temp)
# -----------------------------
with st.expander("🫀 Optional physiology (if wearing a device)"):
    colp1, colp2 = st.columns(2)
    with colp1:
        rmssd_ms = st.number_input("HRV (RMSSD, ms)", min_value=0.0, step=1.0, help="Enter resting RMSSD if available.")
    with colp2:
        skin_temp_c = st.number_input("Skin temperature (°C)", min_value=0.0, step=0.1, help="Wrist or skin thermistor.")

# -----------------------------
# 6) Sensor Snapshot (optional manual entry)
# -----------------------------
with st.expander("🔎 Light & Air snapshot (optional)"):
    coll1, coll2 = st.columns(2)
    with coll1:
        light_lux = st.number_input("Light level (lux)", min_value=0.0, step=1.0)
    with coll2:
        co2_ppm = st.number_input("CO₂ level (ppm)", min_value=0.0, step=50.0)

st.markdown("---")

# -----------------------------
# Mini dashboard (pretty summary chips/cards)
# -----------------------------
st.subheader("Now")
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
with mc1:
    metric_card("KSS (sleepiness)", f"{kss_score}", "1 alert → 9 very sleepy", "🛌")
with mc2:
    metric_card("HRV (RMSSD)", f"{rmssd_ms if rmssd_ms else '—'} ms", "higher often → calmer", "🫀")
with mc3:
    metric_card("Skin Temp", f"{skin_temp_c if skin_temp_c else '—'} °C", "wrist/proximal", "🌡️")
with mc4:
    metric_card("Light", f"{light_lux if light_lux else '—'} lux", "task plane", "💡")
with mc5:
    metric_card("CO₂", f"{co2_ppm if co2_ppm else '—'} ppm", "ventilation proxy", "🫧")

st.markdown("---")

# -----------------------------
# 7) Clothing (what are you wearing)
# -----------------------------
st.header("5) What are you wearing?")
clothing_choice = st.selectbox("Select your main clothing layer:", ["T-shirt", "Sweater", "Jacket", "Coat", "Other"])
clothing_other = st.text_input("Please specify:") if clothing_choice == "Other" else ""

st.markdown("---")

# -----------------------------
# Actions: Reset + Submit
# -----------------------------
a1, a2 = st.columns([1, 2])
with a1:
    if st.button("Reset form"):
        st.rerun()

with a2:
    if st.button("Submit Feedback", type="primary"):
        data = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "room": (room or None),
            "user_id": (user_id or None),

            # feeling
            "mood": (mood_other.strip() if mood == "Other" else mood),
            "feeling_notes": (feeling_notes.strip() or None),

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

            # KSS / physiology / sensors
            "kss_score": kss_score,
            "rmssd_ms": (float(rmssd_ms) if rmssd_ms else None),
            "skin_temp_c": (float(skin_temp_c) if skin_temp_c else None),
            "light_lux": (float(light_lux) if light_lux else None),
            "co2_ppm": (float(co2_ppm) if co2_ppm else None),

            # clothing
            "clothing": (clothing_choice if clothing_choice != "Other" else (clothing_other.strip() or None)),
        }

        try:
            supabase.table("feedback").insert(data).execute()
            st.success("✅ Thanks! Your feedback was submitted.")
            st.rerun()  # clear the form after success
        except Exception as e:
            st.error(f"❌ Failed to submit: {e}")

