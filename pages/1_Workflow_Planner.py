from __future__ import annotations
import io
import streamlit as st
import matplotlib.pyplot as plt  # noqa: F401  (used by generated code)
from utils.styles import inject_base_styles
from utils.gemini_client import setup_gemini

inject_base_styles()
st.title("Agent Workflow Planner")

prompt = st.text_area("Enter your idea or task for the agent:")

client = setup_gemini()

colA, colB = st.columns(2)

with colA:
    if st.button("Generate Workflow Text", use_container_width=True) and prompt:
        gemini_prompt_text = (
            f"You are an expert workflow designer. The user has an idea: '{prompt}'.\n"
            "Generate a detailed, step-by-step ~500-word workflow that an AI agent should follow to accomplish this task.\n"
            "Break into clear phases, include decision points if needed, be practical and logically ordered.\n"
        )
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=gemini_prompt_text,
            )
            workflow_text = getattr(response, "text", None) or "No content returned."
            st.subheader("Proposed Agent Workflow")
            st.write(workflow_text)
        except Exception as e:
            st.error(f"Error generating workflow: {e}")

with colB:
    if st.button("Generate Workflow Diagram", use_container_width=True) and prompt:
        gemini_prompt_diagram = (
            f"Write Python code using matplotlib.pyplot and matplotlib.patches to draw a workflow diagram for the idea: '{prompt}'. "
            "The code should define workflow steps, draw labeled boxes with arrows, and create a matplotlib figure object named 'fig'. "
            "Do not include any code for displaying or saving the image."
        )
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=gemini_prompt_diagram,
            )
            code = getattr(response, "text", "")

            # Execute generated code skipping the first/last lines if fenced code is returned
            code_lines = code.splitlines()
            if len(code_lines) >= 2 and code_lines[0].strip().startswith("```"):
                # Strip fences
                inner = []
                for line in code_lines[1:]:
                    if line.strip() == "```":
                        break
                    inner.append(line)
                code_to_exec = "\n".join(inner)
            else:
                code_to_exec = code

            local_vars = {}
            try:
                exec(code_to_exec, {"plt": plt}, local_vars)
            except Exception as e:
                st.error(f"Error executing generated code: {e}")
                st.code(code_to_exec, language="python")
                raise

            fig = local_vars.get("fig", None)
            if fig is not None:
                buf = io.BytesIO()
                fig.savefig(buf, format="png", bbox_inches="tight")
                buf.seek(0)
                st.image(buf, caption="Generated Workflow Diagram")
            else:
                st.error("No figure named 'fig' was created by generated code.")
        except Exception as e:
            st.error(f"Error generating diagram: {e}")
