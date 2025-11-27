import streamlit as st

# --- Session State Initialization ---
# Initialize the content of the editor. This variable will hold the actual text.
if 'editor_content' not in st.session_state:
    st.session_state.editor_content = ""
# Initialize the current file name. Used for display and as a default for saving.
if 'current_file_name' not in st.session_state:
    st.session_state.current_file_name = "untitled.txt"
# Initialize the value for the filename input widget used when saving.
if 'filename_input_value' not in st.session_state:
    st.session_state.filename_input_value = "untitled.txt"


# --- Page Configuration ---
st.set_page_config(
    page_title="Streamlit Text Editor",
    page_icon="✍️",
    layout="wide"  # Use a wide layout for better text editing experience
)

# --- Title and Header ---
st.title("✍️ Simple Streamlit Text Editor")
st.markdown("Edit text, upload files, and save your work directly from your browser.")

# --- Callbacks for button actions ---

def new_file():
    """Clears the editor content and resets the file name."""
    st.session_state.editor_content = ""
    st.session_state.current_file_name = "untitled.txt"
    st.session_state.filename_input_value = "untitled.txt"
    st.success("New file created! Editor cleared.")
    # A rerun is necessary to immediately update the `st.text_area` and `st.text_input` widgets
    st.experimental_rerun()

def update_current_file_name_from_input():
    """
    Updates the session state's 'current_file_name' with the value from the
    'filename_input_value' widget. This keeps the displayed filename in sync.
    """
    st.session_state.current_file_name = st.session_state.filename_input_value

# --- File Operations (Open) ---
st.subheader("📂 Open File")
uploaded_file = st.file_uploader(
    "Upload a text file to open:",
    type=['txt', 'py', 'md', 'json', 'csv', 'html', 'css', 'js', 'log'], # Common text-based file types
    help="Select a text-based file from your computer to load its content into the editor."
)

if uploaded_file is not None:
    try:
        # Read the file content, assuming UTF-8 encoding
        file_contents = uploaded_file.read().decode('utf-8')
        
        # Update session state variables with the loaded file's data
        st.session_state.editor_content = file_contents  # Update editor content
        st.session_state.current_file_name = uploaded_file.name  # Update current file name
        st.session_state.filename_input_value = uploaded_file.name  # Update the save input field
        
        st.success(f"File '{uploaded_file.name}' loaded successfully!")
        
        # A rerun is essential here to force the `st.text_area` and `st.text_input`
        # widgets to re-render with the new content from session state.
        st.experimental_rerun()
    except UnicodeDecodeError:
        st.error(f"Error: Could not decode '{uploaded_file.name}' as UTF-8. Please ensure it's a plain text file.")
    except Exception as e:
        st.error(f"An unexpected error occurred while reading the file: {e}")

# --- Text Editor Area ---
st.subheader("📝 Editor")
st.text_area(
    "Edit your text here:",
    value=st.session_state.editor_content,  # Initial value is from session state
    height=500,  # Set a reasonable height for the editor
    key="editor_content",  # The key automatically updates st.session_state.editor_content on user input
    help="Type or paste your text here. All changes are automatically saved to the editor's state."
)


# --- Action Buttons (New, Save) ---
st.subheader("🚀 Actions")
col1, col2 = st.columns([1, 2]) # Use columns to arrange buttons nicely

with col1:
    st.button(
        "✨ New File",
        on_click=new_file,
        help="Click to clear the editor content and start fresh with an 'untitled.txt' file."
    )

with col2:
    # Text input for filename for saving
    st.text_input(
        "Filename to save as:",
        value=st.session_state.current_file_name,  # Initialize with the current file name
        key="filename_input_value",  # This key automatically updates st.session_state.filename_input_value
        on_change=update_current_file_name_from_input, # Optional: sync current_file_name when user changes this input
        help="Enter the desired filename (e.g., my_document.txt, script.py, readme.md)"
    )

    # Download button for saving
    st.download_button(
        label="💾 Download File",
        # The content to download comes directly from the editor's session state
        data=st.session_state.editor_content.encode('utf-8'),
        # The filename for the download comes from the user-editable input field
        file_name=st.session_state.filename_input_value,
        mime="text/plain",  # Default MIME type for plain text files
        help="Click to download the current editor content as a file to your computer."
    )

st.markdown("---")
st.info("Tip: After making changes, you can simply click 'Download File' to save your work. The filename can be changed above.")

# Optional: Display current session state for debugging purposes
# st.expander("Current Session State (for debugging)").json(st.session_state.to_dict())
