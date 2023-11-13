import streamlit as st
import os
from dotenv import load_dotenv
from openai import OpenAI
import time

# Load environment variables
load_dotenv()

# App title
st.set_page_config(page_title="🤗💬 Jewel")

# OpenAI API Key
import os
import streamlit as st

# Start of the Streamlit sidebar
with st.sidebar:
    # Streamlit UI setup for title
    st.markdown("""
        <h1 style="text-align: center">
        Software Aus Polen<br><br> <img src="https://raw.githubusercontent.com/JHFVR/jle/main/jle_blue.svg" width="50px" height="50px" /> <br><br>
        </h1>
        """, unsafe_allow_html=True)

    # Check if running in a Cloud Foundry environment
    if 'VCAP_SERVICES' in os.environ or 'VCAP_APPLICATION' in os.environ:
        # Cloud Foundry specific behavior
        if 'OPENAI_API_KEY' in os.environ:
            st.success('OpenAI API key already provided!', icon='✅')
            st.session_state.openai_api_key = os.environ['OPENAI_API_KEY']
        else:
            openai_api_key = st.text_input('Enter OpenAI API key:', type='password')
            if openai_api_key:
                # Store the API key in Streamlit session state
                st.session_state.openai_api_key = openai_api_key
                st.success('API key stored in session for Cloud Foundry. Proceed to chat!', icon='👉')
            else:
                st.warning('Please enter your API key!', icon='⚠️')
    else:
        # Behavior for non-Cloud Foundry environments
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

    # some more info
    st.markdown('<br><br>', unsafe_allow_html=True)
    
    st.markdown('📖 Here\'s where you can generate your OpenAI API key: https://help.openai.com/en/articles/4936850-where-do-i-find-my-api-key')

    st.markdown('<br>', unsafe_allow_html=True)

    st.markdown('🐙 Github: Here\'s the link to the project on Github: https://github.com/JHFVR/glowing-octo-enigma/')

# Load credentials of fetch from variable:
load_dotenv()

# Initialize OpenAI client with the API key from session state
if 'openai_api_key' in st.session_state:
    client = OpenAI(api_key=st.session_state.openai_api_key)
else:
    client = OpenAI()

# Check if assistant and thread are already created
if 'assistant_id' not in st.session_state or 'thread_id' not in st.session_state:
    # Create an assistant and a thread
    assistant = client.beta.assistants.create(
        name="Streamlit Jewel",
        instructions="You are a helpful assistant running within enterprise software. Answer to the best of your knowledge, be truthful if you don't know. Concise answers, no harmful language or unethical replies.",
        tools=[{"type": "code_interpreter"}],
        model="gpt-4-1106-preview"
    )
    thread = client.beta.threads.create()

    # Store the IDs in session state
    st.session_state.assistant_id = assistant.id
    st.session_state.thread_id = thread.id
else:
    # Use existing IDs
    assistant_id = st.session_state.assistant_id
    thread_id = st.session_state.thread_id

def display_messages(thread_id):
    thread_messages = client.beta.threads.messages.list(thread_id).data
    # Reverse the order of messages for display
    thread_messages.reverse()
    # Clear previous messages (if any)
    if 'message_display' in st.session_state:
        for container in st.session_state.message_display:
            container.empty()
    st.session_state.message_display = []
    for message in thread_messages:
        role = message.role
        for content_item in message.content:
            message_text = content_item.text.value
            # Store each message container in session state
            container = st.container()
            with container:
                with st.chat_message(role, avatar='https://raw.githubusercontent.com/JHFVR/jle/main/jle_blue.svg' if role == "assistant" else None):
                    st.write(message_text)
            st.session_state.message_display.append(container)

# Display an initial greeting message
if 'initialized' not in st.session_state:
    with st.chat_message("assistant", avatar='https://raw.githubusercontent.com/JHFVR/jle/main/jle_blue.svg'):
        st.write("Hi - how may I assist you today?")
    st.session_state.initialized = False

def wait_on_run(run, thread_id):
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run

# User-provided prompt
if prompt := st.chat_input(disabled=not openai_api_key):
    if not st.session_state.initialized:
        # Create an assistant and a thread
        assistant = client.beta.assistants.create(
            name="Streamlit Jewel",
            instructions="You are a helpful assistant running within enterprise software. Answer to the best of your knowledge, be truthful if you don't know. Concise answers, no harmful language or unethical replies.",
            tools=[{"type": "code_interpreter"}],
            model="gpt-4-1106-preview"
        )
        thread = client.beta.threads.create()

        # Store the IDs in session state
        st.session_state.assistant_id = assistant.id
        st.session_state.thread_id = thread.id

        # Mark as initialized
        st.session_state.initialized = True

  # Post user message
    user_message = client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt
    )

    # Create a run for the assistant to process the conversation
    run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=st.session_state.assistant_id,
        instructions="Please address the user appropriately."
    )

    # Wait for the run to complete
    completed_run = wait_on_run(run, st.session_state.thread_id)

    # Retrieve and display updated messages
    display_messages(st.session_state.thread_id)