import uuid
from datetime import datetime, timezone
import streamlit as st
from supabase import create_client, Client
from ui_helpers import yes_no_matrix, likert_matrix, who5_matrix

st.set_page_config(page_title="Extended Environment Survey", page_icon="📊")

SUPABASE_URL = st.secrets["SUPABASE_URL"].strip().rstrip("/")
SUPABASE_KEY = st.secrets["SUPABASE_KEY"].strip()
EXTENDED_TABLE = st.secrets.get("SUPABASE_EXTENDED_TABLE", "extended_feedback")

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

st.title("Extended Environment Survey")
st.caption("This section captures broader environmental satisfaction, symptoms, and well-being.")

room = st.text_input("Room/Location (optional)")
user_id = st.text_input("User ID (optional)")
grid_number = st.number_input("Seat/grid number (optional)", min_value=1, max_value=120, value=1, step=1)

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
symptoms = yes_no_matrix("Symptoms", symptom_questions, key_prefix="symptom")
symptom_notes = st.text_area("Symptoms notes (optional)")

satisfaction_questions = [
    ("overall", "How satisfied are you with the overall indoor environment of the classroom/studio?"),
    ("privacy", "How satisfied are you with the level of privacy during class or studio work?"),
    ("layout", "How satisfied are you with the layout and spatial organization of the classroom/studio?"),
    ("appearance", "How satisfied are you with the color, decoration, or visual appearance of the space?"),
    ("airmove", "How satisfied are you with the air movement or ventilation in the space?"),
    ("clean", "How satisfied are you with the cleanliness and hygiene of the environment?"),
    ("view", "How satisfied are you with the outdoor view or visual connection to the outside environment?"),
]
satisfaction = likert_matrix("Satisfaction with the Space (1–5)", satisfaction_questions, key_prefix="sat")
satisfaction_notes = st.text_area("Satisfaction notes (optional)")

who_answers, who_raw, who_scaled = who5_matrix()

if st.button("Submit Extended Survey", type="primary"):
    payload = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "room": room.strip() or None,
        "user_id": user_id.strip() or None,
        "grid_number": int(grid_number) if grid_number else None,
        "symptom_notes": symptom_notes.strip() or None,
        "satisfaction_notes": satisfaction_notes.strip() or None,
        "who5_raw_sum": who_raw,
        "who5_scaled_0_100": who_scaled,
    }

    payload.update(symptoms)
    payload.update(satisfaction)
    payload.update(who_answers)

    try:
        supabase.table(EXTENDED_TABLE).insert(payload).execute()
        st.success("✅ Extended survey submitted successfully.")
    except Exception as e:
        st.error(f"❌ Failed to submit: {e}")
