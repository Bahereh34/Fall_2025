import streamlit as st
import streamlit as st

def yes_no_matrix(title, questions, key_prefix):
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


def likert_matrix(title, questions, key_prefix):
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


def who5_matrix(title="Well-Being (WHO-5)"):
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
