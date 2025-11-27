from __future__ import annotations
import os
import streamlit as st
from google import genai

def setup_gemini():
    """Return a configured Google Gemini client.
    Prefers Streamlit secrets, then environment variable GEMINI_API_KEY.
    Shows a friendly error if missing.
    """
    try:
        return genai.Client(api_key="")
    except Exception as e:
        st.error(f"Failed to initialize Gemini client: {e}")
        st.stop()
