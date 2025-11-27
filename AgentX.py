# index.py
from __future__ import annotations
import streamlit as st
from utils.styles import inject_base_styles
import os

inject_base_styles()

st.markdown("<h1>Welcome to <u>AgentX</u></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; font-size:18px;'>Streamline creation and deployment of AI agents with ease.</p>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        """<div class="feature-card">
        <h3>🔹 Enhance Context of LLMs</h3>
        Customize large language models for specific tasks using <b>Retrieval Augmented Generation (RAG)</b>.
        </div>""", unsafe_allow_html=True
    )
with col2:
    st.markdown(
        """<div class="feature-card">
        <h3>🔹 Add External Sources</h3>
        Dynamically incorporate relevant info via <b>Custom Connector</b> for context-aware outputs.
        </div>""", unsafe_allow_html=True
    )
with col3:
    st.markdown(
        """<div class="feature-card">
        <h3>🔹 Multi-Agent Systems</h3>
        Enable collaboration and task management among multiple AI agents.
        </div>""", unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# Helpful links to pages (works on Streamlit >= 1.32). Fallback text if not available.
try:
    st.page_link("pages/1_Workflow_Planner.py", label="🚀 Go to Workflow Planner", icon="🧭")
    st.page_link("pages/2_Build_Agent.py", label="🛠️ Go to Agent Builder", icon="🧩")
    st.page_link("pages/3_My_Agents.py", label="📁 My Agents", icon="📂")
    st.page_link("pages/4_Multi_Agent_System.py", label="🤖 Multi-Agent System", icon="🔗")
    st.page_link("pages/5_Agent_MarketPlace.py", label="📂 Agent MarketPlace", icon="📂")
except Exception:
    st.info("Use the sidebar to open “Workflow Planner”, “Agent Builder”, “My Agents”, and “Multi-Agent System”.")
