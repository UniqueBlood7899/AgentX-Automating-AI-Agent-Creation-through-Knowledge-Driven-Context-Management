# pages/4_Multi_Agent_System.py
from __future__ import annotations
import os
import sys
import shlex
import subprocess
from pathlib import Path
import streamlit as st
import re
from utils.gemini_client import setup_gemini

# If you use a helper to create a Gemini client (like setup_gemini), import it.
# from utils.gemini_client import setup_gemini

st.set_page_config(page_title="Multi-Agent System", page_icon="🤖")

st.title("🤖 Multi-Agent System Builder")
st.write(
    "Select agents in `./agents/`, describe how they should connect/coordinate, and generate a new orchestrator agent."
)

AGENTS_DIR = Path.cwd() / "agents"
AGENTS_DIR.mkdir(parents=True, exist_ok=True)

# Utility: sanitize filenames
def sanitize_filename(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[^A-Za-z0-9_-]", "_", name)
    if not name:
        name = "multi_agent"
    return name

# Utility: build a cross-platform streamlit run command (no POSIX-only single quotes)
def build_streamlit_run_cmd(path: Path) -> str:
    if os.name == "nt":  # Windows
        return f'python -m streamlit run "{str(path)}"'
    else:
        return f"python3 -m streamlit run {shlex.quote(str(path))}"

# List available agents
agent_files = sorted([p for p in AGENTS_DIR.glob("*.py") if p.is_file()])

if not agent_files:
    st.info("No agents found in `./agents/`. Create agents first in Agent Builder.")
    st.stop()

# Show list and allow multi-select
agent_names = [p.name for p in agent_files]
selected = st.multiselect("Select agents to include in the multi-agent system", options=agent_names, default=[])

st.markdown("---")
st.subheader("How should the agents be connected?")
st.write("Write a short prompt describing how selected agents should interact, responsibilities, communication channels, and any orchestration rules.")
connection_prompt = st.text_area(
    "Describe agent connections and orchestration (example: 'Agent A listens for new documents and notifies Agent B to summarize; Agent C evaluates summaries and stores metadata')",
    height=180,
    placeholder="Describe how agents should collaborate and what the orchestrator should do..."
)

st.markdown("---")
st.subheader("Generation options")

with st.expander("Advanced options", expanded=False):
    orchestrator_filename = st.text_input("Generated orchestrator filename (no extension)", value="orchestrator_agent", help="File will be saved into ./agents/")
    run_with_streamlit = st.checkbox("Run generated orchestrator with `streamlit run` after creation", value=False)
    gemini_api_key = st.text_input("Optional Gemini API key (used only in example code placeholders)", type="password")
    model_name = st.text_input("Model to reference in example code", value="gemini-2.5-flash")

# Prepare submit
if "generated_multi_agent" not in st.session_state:
    st.session_state["generated_multi_agent"] = None
if "generated_multi_agent_path" not in st.session_state:
    st.session_state["generated_multi_agent_path"] = ""

# Show selected agents preview
if selected:
    st.markdown("**Selected agents**")
    for name in selected:
        p = AGENTS_DIR / name
        try:
            text = p.read_text(encoding="utf-8")
            preview = text[:600] + ("...\n(Preview truncated)" if len(text) > 600 else "")
            st.code(preview, language="python")
        except Exception as e:
            st.error(f"Unable to read `{name}`: {e}")

# Use a form to bundle inputs and avoid lost clicks
with st.form("multi_agent_form"):
    submitted = st.form_submit_button("Generate Multi-Agent Orchestrator")

if submitted:
    if not selected:
        st.error("Select at least one agent.")
    elif not connection_prompt.strip():
        st.error("Provide a description of how the agents are connected.")
    else:
        # Build prompt for model (concise but explicit)
        agents_list_text = "\n".join([f"- {name}: path='./agents/{name}'" for name in selected])
        full_prompt = f"""
You are asked to generate a Python Streamlit orchestrator agent that combines multiple existing agents into a single application.
Agents:
{agents_list_text}

Connection / orchestration description:
{connection_prompt.strip()}

Combine the functionality of the selected agents into a application that coordinates their actions as described.

Output only the Python file contents inside a fenced code block (```python ... ```). Do not include any extra commentary outside code fences.
"""

        # If you maintain a helper to create a Gemini client, call it here. Otherwise, assume the generator
        # will include placeholder snippet. The user previously used `client = setup_gemini()`.
        try:
            # Attempt to use existing client if present in globals/session_state
            client = None
            if "client" in globals():
                client = globals()["client"]
            elif "client" in st.session_state:
                client = st.session_state["client"]
            # If you want to force using setup_gemini, uncomment the import & call below:
            # from utils.gemini_client import setup_gemini
            client = setup_gemini()

            if client:
                response = client.models.generate_content(model=model_name, contents=full_prompt)
                raw = (getattr(response, "text", "") or "").strip()
            else:
                # If no client available, create a helpful template prompt and fallback to a simple generator
                st.warning("No Gemini client found in runtime — inserting a template orchestrator. If you want model-generated code, initialize `client` (setup_gemini) or provide a Gemini API key.")
                raw = None
        except Exception as e:
            st.error(f"Error generating orchestrator: {e}")
            raw = None

        # If model returned content, extract fenced code; otherwise use a simple template
        cleaned_code = ""
        if raw:
            # extract python fenced code if present
            if "```" in raw:
                lines = raw.splitlines()
                start = end = None
                for i, line in enumerate(lines):
                    if line.strip().startswith("```python"):
                        start = i
                    elif line.strip() == "```" and start is not None and end is None:
                        end = i
                        break
                if start is not None and end is not None and end > start:
                    cleaned_code = "\n".join(lines[start + 1 : end])
                else:
                    cleaned_code = raw
            else:
                cleaned_code = raw
        else:
            # Fallback template (simple orchestrator)
            sanitized_name = sanitize_filename(orchestrator_filename if orchestrator_filename else "orchestrator_agent")
            cleaned_code = f'''"""
Unable to Genetate orchestrator via Gemini model.
'''

        # Save cleaned_code to session_state so UI can show it and allow saving
        st.session_state["generated_multi_agent"] = cleaned_code

        st.subheader("🔹 Generated Code")
        st.code(cleaned_code, language="python")

        app_file = "generated_app.py"
        st.session_state["generated_app_file"] = app_file
        try:
            with open(app_file, "w", encoding="utf-8") as f:
                f.write(cleaned_code)
            st.success(f"✅ App saved as `{app_file}`")

            st.markdown(
                f"""
                ### ▶️ Running App...
                In case it doesn’t open automatically, run:

                ```bash
                python -m streamlit run app.py
                ```
                """
            )
        
            # Auto-launch generated app
            try:
                if sys.platform == "win32":
                    # Use start to open a new cmd window and run the streamlit app
                    subprocess.Popen(f'start cmd /k python -m streamlit run app.py', shell=True)
                else:
                    # many Linux desktops provide x-terminal-emulator; if not available this will silently fail
                    subprocess.Popen(["x-terminal-emulator", "-e", "streamlit", "run", app_file])
            except Exception:
                # non-fatal: just continue
                pass

        except Exception as e:
            st.error(f"⚠️ Error while saving or launching generated code: {e}")

        # save_form_key = f"save_multi_{suggested_name}"
        # with st.form(f"{save_form_key}_form"):
        #     filename_input = st.text_input("Orchestrator filename (no extension)", value=suggested_name, key=f"save_name_{suggested_name}")
        #     overwrite_checkbox = False
        #     final_path = AGENTS_DIR / f"{sanitize_filename(st.session_state.get(f'save_name_{suggested_name}', suggested_name))}.py"
        #     if final_path.exists():
        #         st.warning(f"`{final_path.name}` already exists.")
        #         overwrite_checkbox = st.checkbox("I understand this will overwrite the existing file", key=f"save_overwrite_{suggested_name}")
        #     save_clicked = st.form_submit_button("Save orchestrator")

        #     if save_clicked:
        #         safe_name = sanitize_filename(st.session_state.get(f"save_name_{suggested_name}", suggested_name))
        #         dest = AGENTS_DIR / f"{safe_name}.py"
        #         try:
        #             if dest.exists() and not st.session_state.get(f"save_overwrite_{suggested_name}", False):
        #                 st.error("File exists and overwrite not confirmed.")
        #             else:
        #                 tmp = str(dest) + ".tmp"
        #                 with open(tmp, "w", encoding="utf-8") as f:
        #                     f.write(st.session_state["generated_multi_agent"])
        #                 os.replace(tmp, dest)
        #                 st.success(f"✅ Orchestrator saved as `./agents/{dest.name}`")
        #                 st.session_state["generated_multi_agent_path"] = str(dest)
        #                 # Optionally run with streamlit
        #                 if run_with_streamlit:
        #                     cmd = build_streamlit_run_cmd(dest)
        #                     st.info(f"Attempting to run: `{cmd}`")
        #                     try:
        #                         # On Windows we need to use shell=True to use start cmd /k, but here we just spawn the process
        #                         subprocess.Popen(cmd, shell=True)
        #                         st.success("Launched orchestrator (background/terminal).")
        #                     except Exception as e:
        #                         st.error(f"Failed to launch orchestrator: {e}")
        #         except Exception as e:
        #             st.error(f"Error saving orchestrator: {e}")

# Show last generated path
if st.session_state.get("generated_multi_agent_path"):
    st.info(f"Last saved orchestrator: `{st.session_state['generated_multi_agent_path']}`")
