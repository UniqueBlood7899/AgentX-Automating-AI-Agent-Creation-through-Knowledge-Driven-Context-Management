# pages/3_My_Agents.py
from __future__ import annotations
import streamlit as st
import os
import sys
import subprocess
import shlex
import signal
from pathlib import Path
from typing import Dict, Optional

st.set_page_config(page_title="Agent MarketPlace", page_icon="📂")

st.title("📁 Agent MarketPlace")
st.write("This page lists Python agent files in `./marketplace/`. Click **Run** to execute an agent (in a separate process).")

AGENTS_DIR = Path.cwd() / "marketplace"
AGENTS_DIR.mkdir(parents=True, exist_ok=True)

# Initialize process registry in session_state (maps agent_name -> dict with 'proc' and 'pid')
if "agent_processes" not in st.session_state:
    st.session_state.agent_processes = {}  # type: ignore

def human_preview(path: Path, max_chars: int = 2000) -> str:
    try:
        text = path.read_text(encoding="utf-8")
        return text[:max_chars] + ("...\n(Preview truncated)" if len(text) > max_chars else "")
    except Exception as e:
        return f"Error reading file: {e}"

def try_open_in_terminal(cmd: str) -> Optional[subprocess.Popen]:
    """
    Try to open a new terminal window and run cmd inside it.
    Returns the Popen object if successful, else None.
    """
    try:
        if sys.platform == "win32":
            # start a new cmd window and run the command; keep it open (/k)
            full = f'start cmd /k {cmd}'
            return subprocess.Popen(full, shell=True)
        elif sys.platform == "darwin":
            # macOS: use osascript to open Terminal and run command
            osa = f'''osascript -e 'tell application "Terminal" to do script "{cmd}"' '''
            return subprocess.Popen(osa, shell=True)
        else:
            # common Linux desktop terminal emulators
            terminals = [
                ["x-terminal-emulator", "-e", cmd],
                ["gnome-terminal", "--", "bash", "-lc", f"{cmd}; exec bash"],
                ["konsole", "-e", f"{cmd}; bash"],
                ["xterm", "-e", f"{cmd}; bash"]
            ]
            for t in terminals:
                try:
                    return subprocess.Popen(t)
                except Exception:
                    continue
    except Exception:
        pass
    return None

def start_agent_process(path: Path, use_streamlit: bool = False) -> Dict:
    """
    Start the agent file as a separate process. Tries to open a new terminal window first.
    If that fails, it starts a detached background process and returns details.
    """
    python_exe = sys.executable or "python"
    if use_streamlit:
        if os.name == "nt":  # Windows
            cmd = f'python -m streamlit run "{str(path)}"'
        else:  # POSIX (Linux/Mac)
            cmd = f"python3 -m streamlit run {shlex.quote(str(path))}"

    else:
        cmd = f"{shlex.quote(python_exe)} {shlex.quote(str(path))}"

    # Try opening in a new terminal window
    p = try_open_in_terminal(cmd)
    if p:
        return {"pid": getattr(p, "pid", None), "proc": p, "cmd": cmd, "terminal": True}

    # Fallback: start a detached background process
    try:
        # On POSIX, use setsid to detach
        if os.name == "posix":
            p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
        else:
            # On Windows, CREATE_NEW_PROCESS_GROUP to detach
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NEW_PROCESS_GROUP)
        return {"pid": getattr(p, "pid", None), "proc": p, "cmd": cmd, "terminal": False}
    except Exception as e:
        return {"pid": None, "proc": None, "cmd": cmd, "terminal": False, "error": str(e)}

def stop_agent_process(entry: dict) -> bool:
    """Attempt to stop a running process entry created by start_agent_process."""
    p: Optional[subprocess.Popen] = entry.get("proc")
    pid = entry.get("pid")
    try:
        if p:
            # Normal termination attempt
            if os.name == "posix":
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)  # try to kill the whole group
            else:
                p.terminate()
            return True
        elif pid:
            # Try killing by pid (less graceful)
            if os.name == "posix":
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            else:
                os.kill(pid, signal.SIGTERM)
            return True
    except Exception:
        try:
            # fallback stronger kill
            if p:
                p.kill()
            elif pid:
                os.kill(pid, signal.SIGKILL)
            return True
        except Exception:
            return False
    return False

# List agent files
agents = sorted([p for p in AGENTS_DIR.glob("*.py") if p.is_file()])

if not agents:
    st.info("No agents found in `./agents/`. Generate an agent in the Agent Builder first.")
else:
    for path in agents:
        name = path.stem
        with st.expander(f"🧾 {name} — {path.name}", expanded=False):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"**Path:** `{path}`")
                st.markdown("**Preview (first 2000 chars):**")
                st.code(human_preview(path), language="python")
                if st.checkbox(f"Show full file `{path.name}`", key=f"show_full_{name}"):
                    try:
                        st.text_area("Full file contents", value=path.read_text(encoding="utf-8"), height=300, key=f"full_{name}")
                    except Exception as e:
                        st.error(f"Error reading file: {e}")
            with col2:
                # show run controls
                running = name in st.session_state.agent_processes and st.session_state.agent_processes[name].get("pid")
                st.markdown("**Run controls**")
                use_streamlit = st.checkbox("Run with `streamlit run`", value=False, key=f"streamlit_run_{name}")
                run_btn = st.button("▶️ Run", key=f"run_{name}")
                stop_btn = st.button("⏹ Stop", key=f"stop_{name}")

                if run_btn:
                    if running:
                        st.warning("Agent appears to be already running. Stop it first if you want to restart.")
                    else:
                        entry = start_agent_process(path, use_streamlit=use_streamlit)
                        st.session_state.agent_processes[name] = entry
                        pid = entry.get("pid")
                        if entry.get("error"):
                            st.error(f"Failed to start agent: {entry.get('error')}")
                        elif pid:
                            st.success(f"Started `{name}` (pid: {pid}) — {'terminal' if entry.get('terminal') else 'background'}")
                        else:
                            st.success(f"Started `{name}` — process started (no pid available)")

                if stop_btn:
                    if not running:
                        st.warning("Agent is not running.")
                    else:
                        entry = st.session_state.agent_processes.get(name, {})
                        ok = stop_agent_process(entry)
                        if ok:
                            st.success("Stopped process.")
                            # remove registry entry
                            st.session_state.agent_processes.pop(name, None)
                        else:
                            st.error("Failed to stop process. You may need to kill it manually.")

                # show status
                if name in st.session_state.agent_processes:
                    entry = st.session_state.agent_processes[name]
                    pid = entry.get("pid")
                    if pid:
                        st.info(f"Running — PID: {pid} ({'terminal' if entry.get('terminal') else 'background'})")
                    else:
                        st.info("Running — process started (no PID available)")
                else:
                    st.info("Not running")

# Utility: show quick actions
st.markdown("---")
st.markdown("**Utilities**")
if st.button("Refresh list"):
    st.experimental_rerun()

st.caption("Tip: agents are read from the `./agents/` folder. Only run code you trust. If your agent is a Streamlit app, toggle 'Run with streamlit run'.")
