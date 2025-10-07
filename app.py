import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import uuid

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="Comfort Feedback", page_icon="📝", layout="centered")

# -----------------------------
# UI helper: gradient legend bar
# -----------------------------
def gradient_legend(colors: list[str], labels: list[str], height: int = 10):
    """
    Draw a horizontal gradient bar with evenly spaced labels underneath.
    Example colors: ["#1e3a8a 0%", "#2563eb 16.6%", ..., "#dc2626 100%"]
    """
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
# 2) Thermal Comfort
# -----------------------------
st.header("2) Thermal Comfort")
thermal_sensation = st.slider(
    "Thermal sensation (ASHRAE 7-point)",
    min_value=-3, max_value=3, value=0,
    help="-3 Cold · -2 Cool · -1 Slightly Cool · 0 Neutral · +1 Slightly Warm · +2 Warm · +3 Hot",
)
# 🔹 Thermal spectrum: cool blue → neutral → hot red
thermal_colors = [
    "#1e3a8a 0%",   # deep blue
    "#2563eb 16.6%",
    "#60a5fa 33.3%",
    "#e5e7eb 50%",  # neutral
    "#fdba74 66.6%",
    "#f97316 83.3%",
    "#dc2626 100%", # red
]
thermal_labels = ["Cold", "Cool", "Slightly cool", "Neutral", "Slightly warm", "Warm", "Hot"]
gradient_legend(thermal_colors, thermal_labels)

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

# 🔸 Visual spectrum: dark → OK → bright yellow
glare_colors = ["#000000 0%", "#6b7280 50%", "#fde047 100%"]
glare_labels = ["Dark", "OK", "Too bright"]
gradient_legend(glare_colors, glare_labels)

task_affected = st.checkbox("Glare/brightness is affecting my task (screen/board/paper)")
visual_notes = st.text_area("Visual notes (optional):", placeholder="e.g., glare on screen; board is hard to read…")

st.markdown("---")

# -----------------------------
# 4) Clothing (what are you wearing)
# -----------------------------
st.header("4) What are you wearing?")
clothing_choice = st.selectbox("Select your main clothing layer:", ["T-shirt", "Sweater", "Jacket", "Coat", "Other"])
clothing_other = st.text_input("Please specify:") if clothing_choice == "Other" else ""

# -----------------------------
# Submit
# -----------------------------
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

        # clothing
        "clothing": (clothing_choice if clothing_choice != "Other" else (clothing_other.strip() or None)),
    }

    try:
        supabase.table("feedback").insert(data).execute()
        st.success("✅ Thanks! Your feedback was submitted.")
    except Exception as e:
        st.error(f"❌ Failed to submit: {e}")
