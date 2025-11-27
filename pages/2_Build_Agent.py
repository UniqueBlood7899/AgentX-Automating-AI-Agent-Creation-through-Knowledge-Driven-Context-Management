from __future__ import annotations
import sys
import subprocess
import os
import re
import streamlit as st
from utils.styles import inject_base_styles
from utils.gemini_client import setup_gemini
from pathlib import Path

inject_base_styles()
st.title("AgentX — Agent Builder")

client = setup_gemini()

app_description = st.text_area(
    "Describe the agent you want to build:",
    height=150,
    placeholder="Example: An app that uploads an image and classifies objects in it." ,
)

col1, col2, col3 = st.columns(3)
with col1:
    req_rag = st.checkbox("Requires RAG", value=False, help="Add Retrieval-Augmented Generation instructions to the system prompt.")
with col2:
    req_mcp = st.checkbox("Requires MCP", value=False, help="Add MCP-specific instructions to the system prompt.")
with col3:
    req_ai = st.checkbox("Requires AI", value=False, help="Add general AI usage instructions to the system prompt.")

# Input for Gemini key (if the user selected Requires AI we show it)
if req_ai:
    st.markdown("---")
    st.info("Provide a Gemini API key to include in generated example code (will only be inserted into the generated code as a placeholder).")
    gemini_api_key = st.text_input("Gemini API key (optional)", type="password")
else:
    gemini_api_key = ""

if st.button("Generate & Show App Code", type="primary"):
    if not app_description.strip():
        st.error("Please enter a description first.")
    else:
        with st.spinner("Generating Streamlit app..."):
            prompt_parts = [f"Write a complete Streamlit app in Python that does the following: {app_description}. Just give the code."]

            if req_rag:
                prompt_parts.append(
                    "Important: The app must include support for Retrieval-Augmented Generation (RAG). Include code that demonstrates connecting to a vector store, embedding text, and performing similarity search to augment model responses. Clearly mark where documents are indexed and queried."
                )
            if req_mcp:
                prompt_parts.append(
                    "Important: The app must integrate with the MCP (Model Control Plane). Add clear placeholders and example code showing how the app would register models, send telemetry, or call MCP endpoints. Explain which values are configurable."
                )
            if req_ai:
                ai_snippet = (
                    "Add an input for a Gemini API key.\n"
                    "Use model `gemini-2.5-flash` from `google.genai`.\n"
                    "Example:\n"
                    "    from google import genai\n"
                    "    client = genai.Client(api_key=user_supplied_key)\n"
                    "    response = client.models.generate_content(model=\"gemini-2.5-flash\", contents=\"Hello\")\n"
                )
                # If user provided a key, we'll add a placeholder replacement instruction so the generated code shows how it could be used.
                if gemini_api_key:
                    ai_snippet += "\nInclude a placeholder variable named USER_GEMINI_KEY set to the user-supplied key."
                prompt_parts.append(ai_snippet)

            full_prompt = "\n\n".join(prompt_parts)
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=full_prompt,
                )
            except Exception as e:
                st.error(f"Error generating app code: {e}")
                st.stop()

            code = (getattr(response, "text", "") or "").strip()
            code_lines = code.splitlines()

            # Try to extract fenced code if present
            cleaned_code = code
            if "```" in code:
                start_index = end_index = None
                for i, line in enumerate(code_lines):
                    if line.strip().startswith("```python"):
                        start_index = i
                    elif line.strip() == "```" and start_index is not None and end_index is None:
                        end_index = i
                        break
                if start_index is not None and end_index is not None and end_index > start_index:
                    cleaned_code = "\n".join(code_lines[start_index + 1:end_index])

            # If user provided a gemini key, optionally inject a placeholder variable into the generated code
            if req_ai and gemini_api_key:
                # naive insertion: add a USER_GEMINI_KEY constant at the top if not present
                if "USER_GEMINI_KEY" not in cleaned_code:
                    cleaned_code = f"USER_GEMINI_KEY = \"{gemini_api_key}\"\n\n" + cleaned_code

            # Persist generated code so it survives Streamlit reruns (so Save Agent works reliably)
            st.session_state["generated_code"] = cleaned_code
            
            st.subheader("🔹 Generated Code")
            st.code(cleaned_code, language="python")

            # Save to file (default behaviour)
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
                    python -m streamlit run {app_file}
                    ```
                    """
                )

                # Auto-launch generated app
                try:
                    if sys.platform == "win32":
                        # Use start to open a new cmd window and run the streamlit app
                        subprocess.Popen(f'start cmd /k python -m streamlit run {app_file}', shell=True)
                    else:
                        # many Linux desktops provide x-terminal-emulator; if not available this will silently fail
                        subprocess.Popen(["x-terminal-emulator", "-e", "streamlit", "run", app_file])
                except Exception:
                    # non-fatal: just continue
                    pass

            except Exception as e:
                st.error(f"⚠️ Error while saving or launching generated code: {e}")

            # ---------------------------
            # NEW: Save agent to ./agents/ as agent_name.py
            # ---------------------------

            # Save agent UI (persistent; uses st.session_state["generated_code"])
# ---------------------------
# SAVE AGENT (robust: read from session_state inside callback)
# ---------------------------
st.markdown("---")
st.subheader("💾 Save Agent (robust)")

# ensure there is code to save
if "cleaned_code" not in globals() and "cleaned_code" not in st.session_state:
    st.error("No generated code to save. Generate the app code first.")
else:
    # prefer session_state copy if present
    code_to_save = st.session_state.get("cleaned_code", globals().get("cleaned_code", ""))

    def sanitize_filename(name: str) -> str:
        name = (name or "").strip()
        name = re.sub(r"[^A-Za-z0-9_-]", "_", name)
        if not name:
            name = "agent"
        return name

    agents_dir = os.path.join(os.getcwd(), "agents")
    os.makedirs(agents_dir, exist_ok=True)

    # session flags to avoid repeated side effects
    if "agent_saved" not in st.session_state:
        st.session_state["agent_saved"] = False
    if "agent_saved_path" not in st.session_state:
        st.session_state["agent_saved_path"] = ""
    if "agent_save_error" not in st.session_state:
        st.session_state["agent_save_error"] = ""

    # if already saved, show stable message and skip the form
    if st.session_state["agent_saved"]:
        st.success(f"✅ Agent already saved as `{st.session_state['agent_saved_path']}`")
        if st.button("Save another agent (clear saved state)"):
            st.session_state["agent_saved"] = False
            st.session_state["agent_saved_path"] = ""
            st.session_state["agent_save_error"] = ""
        else:
            st.stop()

    # callback reads values directly from session_state keys
    def _save_agent_callback():
        # read values from session_state (keys below must match the widget keys)
        raw_name = st.session_state.get("form_agent_name", "")  # <- KEY used by text_input below
        overwrite = st.session_state.get("form_overwrite", False)  # <- KEY used by checkbox below
        safe_name = sanitize_filename(raw_name)
        final_path = os.path.join(agents_dir, f"{safe_name}.py")

        try:
            if os.path.exists(final_path) and not overwrite:
                st.session_state["agent_save_error"] = "File exists and overwrite not confirmed."
                return
            tmp_path = final_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(code_to_save)
            os.replace(tmp_path, final_path)
            st.session_state["agent_saved"] = True
            st.session_state["agent_saved_path"] = f"./agents/{safe_name}.py"
            st.session_state["agent_save_error"] = ""
        except Exception as e:
            st.session_state["agent_save_error"] = f"Error saving agent: {e}"

    # The form: NOTE the widget keys below match what the callback reads
    with st.form("save_agent_form_robust"):
        st.text_input(
            "Agent filename (no extension)",
            placeholder="my_agent",
            key="form_agent_name",  # important: matches the session_state key read in callback
        )

        # show overwrite checkbox only if file exists (we must compute preview path from current name)
        preview_name = sanitize_filename(st.session_state.get("form_agent_name", ""))
        preview_path = os.path.join(agents_dir, f"{preview_name}.py")
        if os.path.exists(preview_path):
            st.warning(f"File `./agents/{preview_name}.py` already exists.")
            st.checkbox(
                "I understand this will overwrite the existing file",
                key="form_overwrite",  # important: matches the session_state key read in callback
            )
        else:
            # ensure key exists so callback can read it (default False)
            if "form_overwrite" not in st.session_state:
                st.session_state["form_overwrite"] = False

        # submit button triggers the callback (no args; callback reads session_state)
        submitted = st.form_submit_button("Save agent", on_click=_save_agent_callback)

    # After form submission the script reruns once, but because the callback wrote session_state flags,
    # we show the saved message above and call st.stop() to keep UI stable.
    if st.session_state.get("agent_save_error"):
        st.error(st.session_state["agent_save_error"])
    else:
        st.info("Saved agents live in the `./agents/` directory. Use the agent filename without `.py` when prompted above.")
