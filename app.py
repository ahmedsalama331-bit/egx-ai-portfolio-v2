import streamlit as st
import pandas as pd
import numpy as np

# ==============================
# 🔐 LOGIN PAGE
# ==============================

st.set_page_config(page_title="EGX AI Portfolio | Secure Login", layout="wide")

# Credentials
VALID_USERNAME = "ahmed"
VALID_PASSWORD = "12345"

# Session state to persist login
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


# ==============================
# 📌 MAIN APP (EGX PORTFOLIO V2)
# ==============================

def run_portfolio_app():
    st.title("📊 EGX AI Portfolio Builder V2")
    st.write("Advanced multi-factor portfolio builder for the Egyptian Stock Market.")

    # Import your actual V2 app logic here
    # Instead of copying the entire long file,
    # we simply import and call its main() function

    import egx_ai_portfolio_app_v2

    


# ==============================
# 🚦 CONTROL FLOW
# ==============================

if not st.session_state.authenticated:
    login_screen()
else:
    run_portfolio_app()
