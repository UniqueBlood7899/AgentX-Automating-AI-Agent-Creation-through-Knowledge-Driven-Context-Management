import os
import json
import numpy as np
import faiss
import streamlit as st
import streamlit.components.v1 as components

from google import genai
from google.genai import types

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Voice Agent with Gemini", page_icon="🎙️")

API_KEY = ""  # <-- put your key or use env var
client = genai.Client(api_key=API_KEY)

# RAG config
EMBED_MODEL = "text-embedding-004"   # same model you used to embed the PDF
INDEX_PATH = "zomato_support.faiss"
CHUNKS_PATH = "zomato_support_chunks.json"
TOP_K = 5  # how many chunks to retrieve


# -----------------------------
# RAG HELPERS (FAISS + Chunks)
# -----------------------------
@st.cache_resource
def load_faiss_index(index_path: str):
    return faiss.read_index(index_path)


@st.cache_resource
def load_chunks(chunks_path: str):
    with open(chunks_path, "r", encoding="utf-8") as f:
        return json.load(f)


# Try loading index + chunks once
RAG_ENABLED = True
try:
    index = load_faiss_index(INDEX_PATH)
    chunks = load_chunks(CHUNKS_PATH)
except Exception as e:
    RAG_ENABLED = False
    index = None
    chunks = []
    st.warning(f"RAG disabled (could not load index/chunks): {e}")


def embed_query(text: str) -> np.ndarray:
    """
    Get a normalized embedding for the query text using Gemini.
    """
    resp = client.models.embed_content(
        model=EMBED_MODEL,
        contents=text,
    )
    vec = np.array(resp.embeddings[0].values, dtype="float32").reshape(1, -1)
    faiss.normalize_L2(vec)
    return vec


def retrieve_relevant_chunks(question_text: str, k: int = TOP_K):
    """
    Retrieve top-k relevant chunks from FAISS index.
    """
    if not RAG_ENABLED or index is None or not chunks:
        return []

    q_vec = embed_query(question_text)
    scores, idxs = index.search(q_vec, k)
    idxs = idxs[0]
    return [chunks[i] for i in idxs if i != -1]


# -----------------------------
# SESSION STATE
# -----------------------------
if "transcript" not in st.session_state:
    st.session_state.transcript = ""

if "answer" not in st.session_state:
    st.session_state.answer = ""


# -----------------------------
# HELPERS
# -----------------------------
def transcribe_with_gemini(uploaded_audio):
    """
    Use Gemini to transcribe the recorded audio.
    """
    if uploaded_audio is None:
        return ""

    # Read audio bytes (Streamlit audio_input returns a WAV file by default)
    audio_bytes = uploaded_audio.getvalue()
    mime_type = uploaded_audio.type or "audio/wav"

    audio_part = types.Part.from_bytes(
        data=audio_bytes,
        mime_type=mime_type,
    )

    prompt = (
        "Transcribe the user's speech. "
        "Return ONLY the raw transcript text, no quotes, labels, or extra words."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, audio_part],
    )

    return (response.text or "").strip()


def ask_gemini(question_text):
    """
    Ask Gemini, but first retrieve relevant chunks from FAISS (RAG).
    Answer concisely, like a Zomato customer support voice agent.
    """
    if not question_text:
        return ""

    # --- RAG retrieval ---
    context_chunks = retrieve_relevant_chunks(question_text)
    context_text = "\n\n---\n\n".join(context_chunks) if context_chunks else ""

    # Build final prompt with context + question
    # If no context available, Gemini will just rely on its own knowledge.
    prompt = f"""
You are a Zomato customer care voice assistant.

Use the provided CONTEXT to answer the user's question.
If the answer is not clearly in the context, say you are not sure and suggest contacting Zomato human support.

CONTEXT:
{context_text if context_text else "[No extra context retrieved from knowledge base]"}

USER QUESTION:
{question_text}
""".strip()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=(
                "You are a voice assistant for Zomato customer support. "
                "Answer concisely in plain text. "
                "Use at most 5 short lines."
            ),
        ),
    )
    return (response.text or "").strip()


def speak_answer_js(text: str):
    """
    Use browser's SpeechSynthesis to speak the answer.
    Runs entirely in the user's browser via JS.
    """
    if not text:
        return

    js_text = json.dumps(text)  # safely escape for JS
    components.html(
        f"""
        <script>
        const utterance = new SpeechSynthesisUtterance({js_text});
        utterance.lang = "en-US";
        window.speechSynthesis.speak(utterance);
        </script>
        """,
        height=0,
    )


# -----------------------------
# UI
# -----------------------------
st.title("🎙️ Voice Agent (Gemini 2.5 Flash + RAG)")
st.caption("Speak your question, confirm the text, then get a Zomato-specific answer with voice playback.")

if RAG_ENABLED:
    st.success("RAG is enabled using zomato_support.faiss and zomato_support_chunks.json.")
else:
    st.info("RAG is currently disabled; answering without FAISS context.")

st.markdown("#### 1️⃣ Record your question")

# Built-in Streamlit audio recorder (includes start/stop mic UI)
audio_value = st.audio_input(
    "Tap the mic to start, speak, then tap to stop.",
    key="voice_input",
    sample_rate=16000,  # good for speech
)

col1, col2 = st.columns(2)
with col1:
    transcribe_btn = st.button("📝 Transcribe", use_container_width=True)
with col2:
    rerecord_btn = st.button("🔁 Clear & re-record", use_container_width=True)

if rerecord_btn:
    st.session_state.transcript = ""
    st.session_state.answer = ""
    st.success("Cleared transcript and answer. You can record again.")

# When user clicks Transcribe
if transcribe_btn:
    if audio_value is None:
        st.warning("Please record your voice first.")
    else:
        with st.spinner("Transcribing with Gemini..."):
            try:
                st.session_state.transcript = transcribe_with_gemini(audio_value)
            except Exception as e:
                st.error(f"Transcription error: {e}")

# -----------------------------
# Show / edit transcript
# -----------------------------
st.markdown("#### 2️⃣ Check your question")

if st.session_state.transcript:
    st.info("Edit the text below if needed, or re-record if it's very wrong.")
else:
    st.caption("Your transcribed text will appear here after you click **Transcribe**.")

st.session_state.transcript = st.text_area(
    "Recognized text:",
    value=st.session_state.transcript,
    height=100,
    placeholder="Transcript will appear here…",
)

# -----------------------------
# Ask Gemini
# -----------------------------
st.markdown("#### 3️⃣ Ask Gemini & listen to the answer")

ask_btn = st.button("🤖 Ask Gemini", type="primary", use_container_width=True)

if ask_btn:
    if not st.session_state.transcript.strip():
        st.warning("Please transcribe and/or enter a question first.")
    else:
        with st.spinner("Getting answer from Gemini (with RAG)..."):
            try:
                st.session_state.answer = ask_gemini(st.session_state.transcript.strip())
            except Exception as e:
                st.error(f"Error calling Gemini: {e}")

# -----------------------------
# Show answer + Speak button
# -----------------------------
if st.session_state.answer:
    st.markdown("##### Answer:")
    st.markdown(st.session_state.answer)

    speak_btn = st.button("🔊 Speak answer", use_container_width=True)
    if speak_btn:
        speak_answer_js(st.session_state.answer)
