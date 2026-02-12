import streamlit as st

def apply_dark_mode():
    dark_css = """
    <style>
        :root {
            --background-color: #0e1117;
            --text-color: #e6edf3;
            --secondary-bg: #161b22;
            --tertiary-bg: #21262d;
            --border-color: #30363d;
            --primary: #58a6ff;
            --primary-hover: #79c0ff;
            --muted: #8b949e;
            --success: #3fb950;
            --danger: #f85149;
        }
        .stApp, [data-testid="stAppViewContainer"] {
            background-color: var(--background-color) !important;
            color: var(--text-color) !important;
        }
        section[data-testid="stSidebar"] {
            background-color: var(--secondary-bg) !important;
            border-right: 1px solid var(--border-color) !important;
        }
        section[data-testid="stSidebar"] * { color: var(--text-color) !important; }
        header, [data-testid="stHeader"], [data-testid="stToolbar"] {
            background: var(--background-color) !important;
            color: var(--text-color) !important;
        }
        h1, h2, h3, h4, h5, h6, p, div, span, label, li {
            color: var(--text-color) !important;
        }
        .stButton > button {
            background-color: var(--tertiary-bg) !important;
            color: var(--text-color) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 6px;
        }
        .stButton > button:hover {
            background-color: #30363d !important;
            border-color: var(--primary) !important;
        }
        .stButton > button[kind="primary"] {
            background-color: var(--primary) !important;
            color: #0d1117 !important;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: var(--primary-hover) !important;
        }
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div > select {
            background-color: var(--tertiary-bg) !important;
            color: var(--text-color) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 6px;
        }
        a { color: var(--primary) !important; }
        a:hover { color: var(--primary-hover) !important; text-decoration: underline; }
    </style>
    """
    st.markdown(dark_css, unsafe_allow_html=True)

def init_theme():
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"
