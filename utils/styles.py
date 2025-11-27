from __future__ import annotations
import streamlit as st

def inject_base_styles():
    st.set_page_config(page_title="AgentX - AI Agent Workflow Planner", layout="wide")
    st.markdown(
        """
        <style>
        .stApp { background: linear-gradient(135deg, #f0f4ff, #d9e4ff); }
        h1 { color: #4B0082; text-align:center; font-family: Helvetica; }
        .feature-card { background-color: #ffffffcc; padding:20px; border-radius:15px; box-shadow:2px 2px 10px rgba(0,0,0,0.1); margin:10px; text-align:center;}
        .stButton>button { background: linear-gradient(90deg, #4B0082, #8A2BE2); color:white; font-weight:bold; }
        a.button-link {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            background: linear-gradient(90deg, #4B0082, #8A2BE2);
            color: white;
            font-weight: bold;
            text-decoration: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
