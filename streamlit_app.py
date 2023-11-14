import streamlit as st
import os
from dotenv import load_dotenv
from openai import OpenAI

from st_pages import Page, show_pages, add_page_title

# App title
st.set_page_config(page_title="Enterprise Assistant", page_icon="💎", layout = 'wide', initial_sidebar_state = 'auto')

with st.sidebar:
    st.sidebar.success("Select a window above.")
    st.markdown('<br><br>', unsafe_allow_html=True)
    st.markdown('Be ready to enter your OpenAI API key when you navigate to the Enterprise Assistant')

# Optional -- adds the title and icon to the current page
add_page_title("Welcome 👋")

# Specify what pages should be shown in the sidebar, and what their titles 
# and icons should be
show_pages(
    [
        Page("streamlit_app.py", "Home", "🏠"),
        Page("pages/1_chat_window.py", "Enterprise Assistant", "💬"),
        Page("pages/2_skills_studio.py", "Skill Studio", "👩‍💻")
    ]
)

# some more info

st.markdown('<br><br>', unsafe_allow_html=True)

st.markdown('📖 Here\'s where you can generate your OpenAI API key: https://help.openai.com/en/articles/4936850-where-do-i-find-my-api-key')

st.markdown('<br>', unsafe_allow_html=True)

st.markdown('🐙 Github: Here\'s the link to the project on Github: https://github.com/JHFVR/glowing-octo-enigma/')