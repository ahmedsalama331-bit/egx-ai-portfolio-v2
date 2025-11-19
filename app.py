import streamlit as st

st.set_page_config(page_title="EGX AI Portfolio | Secure Login", layout="wide")

# Read credentials from secrets.toml
VALID_USERNAME = st.secrets.get("EGX_USERNAME")
VALID_PASSWORD = st.secrets.get("EGX_PASSWORD")

# Session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def login_screen():
    st.title("🔐 Secure Login")
    st.write("Please enter your credentials to access the application.")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            st.session_state.authenticated = True
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("❌ Wrong username or password")


def run_portfolio_app():
    st.title("📊 EGX AI Portfolio Builder V2")

    try:
        import egx_ai_portfolio_app_v2
    except Exception as e:
        st.error(f"⚠️ Error loading app: {e}")
        st.stop()


# -------------------------
# CONTROL FLOW
# -------------------------
if not st.session_state.authenticated:
    login_screen()
else:
    run_portfolio_app()
