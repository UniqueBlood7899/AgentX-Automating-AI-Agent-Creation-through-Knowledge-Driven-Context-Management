# streamlit_app.py
import os
import traceback
import streamlit as st
from dotenv import load_dotenv
import psycopg2
from google import genai

st.set_page_config(page_title="AI + Supabase (psycopg2)", page_icon="🧠", layout="centered")
st.title("🧠🔗 AI-Powered Supabase Ops (psycopg2)")

# -------------------------------
#  1) GEMINI API KEY INPUT
# -------------------------------
with st.expander("1) Enter your Gemini API key", expanded=True):
    st.write("Your key is used only in this session.")
    user_key = st.text_input("Gemini API Key", type="password", value=st.session_state.get("gemini_api_key", ""))

    if user_key:
        st.session_state["gemini_api_key"] = user_key

# Create a Gemini client if key provided
client = None
if st.session_state.get("gemini_api_key"):
    try:
        client = genai.Client(api_key=st.session_state["gemini_api_key"])
        st.success("Gemini client configured.")
    except Exception as e:
        st.error(f"Failed to init Gemini: {e}")

# -------------------------------
#  2) DATABASE CONNECTION (psycopg2)
#     Uses environment variables by default.
# -------------------------------
with st.expander("2) Database connection (from environment variables)", expanded=True):
    st.caption("The app loads a .env automatically if present. You can also override below.")
    load_dotenv(override=False)

    # Show current env-derived values (masked where sensible)
    def envval(name, default=""):
        return os.getenv(name, default)

    col1, col2 = st.columns(2)
    with col1:
        user_env = st.text_input("USER (env: user)", value=envval("user", ""), key="db_user")
        host_env = st.text_input("HOST (env: host)", value=envval("host", ""), key="db_host")
        db_env   = st.text_input("DBNAME (env: dbname)", value=envval("dbname", ""), key="db_name")
    with col2:
        port_env = st.text_input("PORT (env: port)", value=envval("port", ""), key="db_port")
        pw_env   = st.text_input("PASSWORD (env: password)", value=envval("password", ""), key="db_pass", type="password")

    # Optionally push overrides into os.environ for this session
    if st.checkbox("Override environment with the values above"):
        os.environ["user"] = user_env
        os.environ["host"] = host_env
        os.environ["dbname"] = db_env
        os.environ["port"] = port_env
        os.environ["password"] = pw_env
        st.info("Environment variables updated for this process.")

    if st.button("Connect"):
        try:
            USER = os.getenv("user")
            PASSWORD = os.getenv("password")
            HOST = os.getenv("host")
            PORT = os.getenv("port")
            DBNAME = os.getenv("dbname")

            if not all([USER, PASSWORD, HOST, PORT, DBNAME]):
                st.error("Missing one or more required env vars: user, password, host, port, dbname.")
            else:
                connection = psycopg2.connect(
                    user=USER,
                    password=PASSWORD,
                    host=HOST,
                    port=PORT,
                    dbname=DBNAME
                )
                cursor = connection.cursor()
                st.session_state["connection"] = connection
                st.session_state["cursor"] = cursor
                st.success("Connection successful!")
        except Exception as e:
            st.error(f"Connection failed: {e}")
            st.code(traceback.format_exc())

# -------------------------------
#  3) PROMPT → CODE → EXECUTE
# -------------------------------
with st.expander("3) Describe the operation you want to do", expanded=True):
    st.caption("Example: 'Create a table students(id serial primary key, name text) and insert two rows', or 'List all rows from public.students'")
    op = st.text_area("Your request", height=120, placeholder="e.g., 'Fetch first 5 rows from public.courses'")

    # Safety confirmation (recommended when executing generated code)
    acknowledge = st.checkbox("I understand this will execute model-generated code against my database.")

    run = st.button("Generate & Run")
    if run:
        if client is None:
            st.error("Please enter a valid Gemini API key first.")
        elif "connection" not in st.session_state or "cursor" not in st.session_state:
            st.error("Please connect to the database first.")
        elif not acknowledge:
            st.warning("Please confirm the safety checkbox before executing.")
        elif not op.strip():
            st.warning("Please enter an operation.")
        else:
            # Build a precise prompt for safe psycopg2 usage
            gemini_prompt = f"""
You are an assistant that writes Python code to perform the requested database operation using psycopg2.

Table: public.courses              Column: course_id            Type: integer
Table: public.courses              Column: course_name          Type: character varying
Table: public.courses              Column: credits              Type: integer
Table: public.courses              Column: department           Type: character varying
Table: public.students             Column: student_id           Type: integer
Table: public.students             Column: first_name           Type: character varying
Table: public.students             Column: last_name            Type: character varying
Table: public.students             Column: enrollment_year      Type: integer

REQUIREMENTS:
- Assume an existing psycopg2 connection 'connection' and cursor 'cursor' are provided.
- Use parameterized queries where applicable (avoid string concatenation with user input).
- If the operation reads rows, fetch them and store in a variable named 'result' (a list of tuples).
- If the operation modifies data (INSERT/UPDATE/DELETE/DDL), execute it; call 'connection.commit()' and set 'result' to a short string summary like "rows_affected=<n>" (when available).
- Do NOT import new libraries; just use 'connection' and 'cursor' already provided.
- Do NOT close the connection or cursor.
- Return ONLY the Python code, no explanations.

The user's request:
\"\"\"{op.strip()}\"\"\"
"""

            try:
                with st.spinner("Generating code with Gemini..."):
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=gemini_prompt
                    )
                    code = (response.text or "").strip()

                if not code:
                    st.error("Model did not return code.")
                else:
                    # st.subheader("Generated code")
                    # st.code(code, language="python")

                    # Prepare safe execution environment
                    safe_globals = {
                        "connection": st.session_state["connection"],
                        "cursor": st.session_state["cursor"],
                        "psycopg2": psycopg2,  # handy for sql.Identifier if the model uses it
                    }
                    safe_locals = {}

                    st.subheader("Execution result")
                    try:
                        code_lines = code.splitlines()
                        if len(code_lines) > 2:
                            exec("\n".join(code_lines[1:-1]) , safe_globals, safe_locals)
                        else:
                            st.error("Generated code is too short to skip first and last lines.")
                        result = safe_locals.get("result", None)

                        if isinstance(result, list):
                            # likely SELECT rows
                            if len(result) == 0:
                                st.info("Query returned 0 rows.")
                            else:
                                st.success(f"Returned {len(result)} row(s).")
                                st.dataframe(result)
                        else:
                            st.write(result if result is not None else "No 'result' variable returned.")
                    except Exception as run_err:
                        st.error("Error while executing generated code:")
                        st.code(traceback.format_exc())

            except Exception as e:
                st.error(f"Failed to generate code: {e}")
                st.code(traceback.format_exc())

# -------------------------------
#  4) OPTIONAL: CLOSE CONNECTION
# -------------------------------
with st.expander("4) Manage session"):
    if "connection" in st.session_state:
        if st.button("Close DB connection"):
            try:
                st.session_state["cursor"].close()
                st.session_state["connection"].close()
                del st.session_state["cursor"]
                del st.session_state["connection"]
                st.success("Connection closed.")
            except Exception as e:
                st.error(f"Error closing connection: {e}")
