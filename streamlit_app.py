import streamlit as st
import os
from dotenv import load_dotenv
from openai import OpenAI

from st_pages import Page, show_pages, add_page_title

# App title
st.set_page_config(page_title="Enterprise Assistant", page_icon="💎", layout = 'wide', initial_sidebar_state = 'auto')

# Initialize session state for page tracking (need that to properly refresh the chat box when i switch pages)
if 'current_page' not in st.session_state:
    st.session_state.current_page = None

if 'previous_page' not in st.session_state:
    st.session_state.previous_page = None

# Update the previous page to the current one, and set the current page as "Chat Window"
st.session_state.previous_page = st.session_state.current_page
st.session_state.current_page = "Home"

## now that freakin sidebar
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
st.markdown('In this app you can test the OpenAI Assistant APIs in action. You can also look up all the skills (tools) that are available and add/delete yourself. The app is built with Streamlit and can run both locally and on CloudFoundry at this point. The skills are stored in a HANA Cloud schema.')

st.markdown('<br><br>', unsafe_allow_html=True)

st.markdown('📖 Here\'s where you can generate your OpenAI API key: https://help.openai.com/en/articles/4936850-where-do-i-find-my-api-key')

st.markdown('<br>', unsafe_allow_html=True)

st.markdown('🐙 Github: Here\'s the link to the project on Github: https://github.com/JHFVR/glowing-octo-enigma/')