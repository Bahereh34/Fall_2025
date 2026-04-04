import streamlit as st

st.set_page_config(page_title="Extended Environment Survey", page_icon="📊")

st.title("Extended Environment Survey")
st.caption("This section captures broader environmental satisfaction, symptoms, and well-being.")


# ---------- 6) Symptoms ----------
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

# ---------- 7) Satisfaction ----------
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
satisfaction_notes = st.text_area(
    "Satisfaction notes (optional)",
    placeholder="Anything to add about comfort, satisfaction, or space quality?",
)
st.markdown("---")

# ---------- 8) WHO-5 ----------
who_answers, who_raw, who_scaled = who5_matrix()
