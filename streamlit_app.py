import streamlit as st
import os
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# App title
st.set_page_config(page_title="🤗💬 Jewel")

# OpenAI API Key
with st.sidebar:
    st.markdown("""
        <h1 style="text-align: center">
        💎💎<br>Software Aus Polen:<br>Jewel<br>💎💎
        </h1>
        """, unsafe_allow_html=True)
    if 'OPENAI_API_KEY' in os.environ:
        st.success('OpenAI API key already provided!', icon='✅')
        openai_api_key = os.environ['OPENAI_API_KEY']
    else:
        openai_api_key = st.text_input('Enter OpenAI API key:', type='password')
        if not openai_api_key:
            st.warning('Please enter your API key!', icon='⚠️')
        else:
            # Save the API key to the .env file
            with open('.env', 'a') as f:
                f.write(f'OPENAI_API_KEY={openai_api_key}\n')
            st.success('API key stored. Proceed to chat!', icon='👉')
    st.markdown('📖 Here\'s where you can generate your OpenAI API key: https://help.openai.com/en/articles/4936850-where-do-i-find-my-api-key')

# Store LLM generated responses
if "messages" not in st.session_state.keys():
    st.session_state.messages = [{"role": "assistant", "content": "How may I help you?"}]

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Function for generating LLM response
def generate_response(prompt_input, api_key):
    openai.api_key = api_key
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt_input,
        max_tokens=150
    )
    return response.choices[0].text.strip()

# User-provided prompt
if prompt := st.chat_input(disabled=not openai_api_key):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

# Generate a new response if last message is not from assistant
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = generate_response(prompt, openai_api_key) 
            st.write(response) 
    message = {"role": "assistant", "content": response}
    st.session_state.messages.append(message)
