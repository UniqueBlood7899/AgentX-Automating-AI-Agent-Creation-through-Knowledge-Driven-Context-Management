# app.py
import streamlit as st
import io
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.patches as patches
import textwrap
from typing import Optional

# --- Replace this with your configured client object (e.g. OpenAI/Google client) ---
# The snippet assumes you already have `client` available and authenticated, as in your example.
# Example placeholder:
# from some_sdk import Client
# client = Client(api_key="YOUR_KEY")
# -------------------------------------------------------------------------------
from google import genai
client = genai.Client(api_key="")  # Add your API key

st.set_page_config(page_title="LLM-driven Visualization App", layout="wide")

st.title("CSV → DataFrame → LLM-generated Visualizations")

st.markdown(
    """
Upload a CSV. The uploaded file will be read into a pandas `df`.  
Enter a prompt describing the plot you want (the LLM will return Python code that creates a matplotlib `fig`).  
Two generate buttons: one for general visualizations (matplotlib + seaborn), one to create a workflow diagram (matplotlib + patches).
"""
)

# --- File uploader and DataFrame creation ---
uploaded_file = st.file_uploader("Upload CSV", type=["csv"], accept_multiple_files=False)

df: Optional[pd.DataFrame] = None
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("CSV loaded into DataFrame `df`.")
        st.write("Preview of `df`:")
        st.dataframe(df)
    except Exception as e:
        st.error(f"Failed to read CSV: {e}")

# Prompt input area
prompt = st.text_area("Visualization prompt (describe the chart you want)", height=140)

st.markdown("---")
col1, col2 = st.columns(2)

# helper: extract code from fenced blocks or return as-is
def extract_code(text: str) -> str:
    """
    Extract python code from triple-fenced blocks if present,
    otherwise return the raw text.
    """
    if not text:
        return ""
    lines = text.splitlines()
    # detect a fence at start
    if len(lines) >= 1 and lines[0].strip().startswith("```"):
        inner = []
        for line in lines[1:]:
            if line.strip().startswith("```"):
                break
            inner.append(line)
        return "\n".join(inner)
    # try to find any fenced blocks in body
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            start = i
            break
    if start is not None:
        inner = []
        for line in lines[start+1:]:
            if line.strip().startswith("```"):
                break
            inner.append(line)
        return "\n".join(inner)
    return text

# helper: run generated code with controlled globals
def run_generated_code(code: str, df_local: Optional[pd.DataFrame]):
    """
    code: python source text that should create a matplotlib.figure named `fig`.
    df_local: the DataFrame to expose as `df` in the exec environment.
    Returns tuple (fig or None, error message or None, executed_code_for_display)
    """
    # sanitize indentation
    code = textwrap.dedent(code)
    # prepare globals/locals for exec
    exec_globals = {
        "plt": plt,
        "sns": sns,
        "pd": pd,
        "np": np,
        "patches": patches,
        # allow access to matplotlib if needed
        "matplotlib": matplotlib,
    }
    # place df in locals (so code can reference df)
    exec_locals = {"df": df_local}
    try:
        exec(code, exec_globals, exec_locals)
    except Exception as e:
        return None, str(e), code
    # The generated code is expected to create 'fig' somehow (e.g. fig = plt.figure(...))
    fig = exec_locals.get("fig") or exec_globals.get("fig")
    return fig, None, code

# The two button actions (visualization, workflow diagram)
with col1:
    if st.button("Generate Visualization (matplotlib + seaborn)", use_container_width=True):
        if not prompt:
            st.error("Please enter a prompt.")
        elif df is None:
            st.error("Please upload a CSV so `df` is available to the generated code.")
        else:
            st.info("Requesting generated code from model...")
            # Build prompt as in your snippet
            cols = df.columns.tolist()
            gemini_prompt = f"""Write Python code using matplotlib.pyplot and seaborn to create the plot described by the user prompt below.
            - Use only the provided pandas DataFrame named `df`. Do NOT create new DataFrames or synthetic/random data.
            - The code must create a matplotlib.figure named `fig` (e.g. `fig, ax = plt.subplots()`).
            - Do not include display or save calls (no plt.show(), fig.savefig()).
            - If a referenced column does not exist in `df`, raise an Exception.

            User prompt:
            \"\"\"{prompt}\"\"\"

            DataFrame columns: {cols}
            DataFrame dtypes: {df.dtypes.to_dict()}

            Return only the Python code block (no extra text)."""

            try:
                # Replace with your client call. Example per your snippet:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=gemini_prompt,
                )
                # try to extract text attribute safely
                code_text = getattr(response, "text", None) or getattr(response, "output", None) or str(response)
                code = extract_code(code_text)
                st.code(code, language="python")
                fig, err, executed_code = run_generated_code(code, df)
                if err:
                    st.error(f"Error executing generated code: {err}")
                    st.subheader("Generated code (for debugging)")
                    st.code(executed_code, language="python")
                elif fig is None:
                    st.error("Generated code did not produce a `fig` object named 'fig'.")
                    st.subheader("Generated code")
                    st.code(executed_code, language="python")
                else:
                    st.success("Visualization generated.")
                    # Display with st.pyplot for matplotlib Figure
                    try:
                        st.pyplot(fig)
                    except Exception:
                        # fallback: save to buffer and display image
                        buf = io.BytesIO()
                        fig.savefig(buf, format="png", bbox_inches="tight")
                        buf.seek(0)
                        st.image(buf)
            except Exception as e:
                st.error(f"Error calling model: {e}")

st.markdown("---")
st.caption(
    "Execution environment exposes: `df` (the uploaded DataFrame), `pd`, `np`, `plt`, `sns`, `patches`, and `matplotlib`.\n"
    "Generated code MUST create a matplotlib.figure object named `fig` (e.g. `fig = plt.figure()` or `fig, ax = plt.subplots()`)."
)
