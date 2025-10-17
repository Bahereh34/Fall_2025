# 03_Voice_Recorder.py
import io, uuid
from datetime import datetime, timezone
import streamlit as st
from supabase import create_client, Client
from audiorecorder import audiorecorder
import speech_recognition as sr

st.title("🎤 Voice Feedback")
st.caption("Record a short voice note; we’ll save the audio + transcript in Supabase.")

# ---- Secrets ----
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BUCKET = st.secrets.get("SUPABASE_BUCKET", "voice-recordings")
TABLE = st.secrets.get("SUPABASE_TABLE", "feedback")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---- Context fields ----
c1, c2 = st.columns(2)
feedback_type = c1.selectbox("Feedback type", ["thermal", "visual", "acoustic", "IAQ", "other"])
room = c2.text_input("Room / Zone ID", placeholder="e.g., ARC_1119")
user_id = st.text_input("User ID (optional)", placeholder="netid or anonymous")

st.subheader("Record")
audio = audiorecorder("🎙️ Start recording", "🛑 Stop")

if len(audio) > 0:
    # to WAV bytes
    wav_bytes = io.BytesIO()
    audio.export(wav_bytes, format="wav")
    wav_bytes.seek(0)

    st.audio(wav_bytes, format="audio/wav")
    st.info(f"Duration: ~{round(len(audio) / 1000, 1)} sec")

    # Transcribe (best-effort)
    transcript = ""
    try:
        st.write("Transcribing…")
        r = sr.Recognizer()
        wav_bytes.seek(0)
        with sr.AudioFile(wav_bytes) as source:
            audio_data = r.record(source)
        transcript = r.recognize_google(audio_data)
        st.success("Transcript ready.")
        st.write("📝", transcript)
    except Exception as e:
        st.warning(f"Transcription skipped: {e}")

    # Save to Supabase
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    fname = f"voice/{ts}_{uuid.uuid4().hex}.wav"

    if st.button("💾 Save voice feedback"):
        try:
            # 1) upload audio
            wav_bytes.seek(0)
            supabase.storage.from_(BUCKET).upload(
                path=fname,
                file=wav_bytes.getvalue(),
                file_options={"content-type": "audio/wav", "x-upsert": "true"},
            )
            # 2) insert row
            supabase.table(TABLE).insert({
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "feedback_type": feedback_type,
                "feedback_text": transcript or None,
                "room": room or None,
                "user_id": user_id or None,
                "audio_path": fname,
                "audio_mime": "audio/wav",
                "source": "fall_2025_app",
            }).execute()
            st.success("✅ Saved! Open the Playback page to listen.")
        except Exception as e:
            st.error(f"❌ Save failed: {e}")
