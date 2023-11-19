import streamlit as st
import os
from dotenv import load_dotenv
from openai import OpenAI
import time
import json
import pandas as pd
import requests
from cfenv import AppEnv
from hdbcli import dbapi
import re

# Load .env file if it exists for local development
load_dotenv()

def get_db_credentials():
    # Check if running on Cloud Foundry
    if 'VCAP_SERVICES' in os.environ:
        env = AppEnv()
        hana_service = env.get_service(label='hana')
        credentials = hana_service.credentials
        return credentials['host'], credentials['port'], credentials['user'], credentials['password']
    else:
        # Load credentials from .env file or environment for local development
        return os.getenv('HANA_HOST'), os.getenv('HANA_PORT'), os.getenv('HANA_USER'), os.getenv('HANA_PASSWORD')

host, port, user, password = get_db_credentials()
conn = dbapi.connect(address=host, port=int(port), user=user, password=password)

def fetch_python_functions():
    with conn.cursor() as cursor:
        cursor.execute("SELECT SkillName, PythonFunction FROM Skills")
        return cursor.fetchall()

def extract_and_run_imports(func_code):
    # Regular expression to match import statements
    import_re = r'^\s*(from\s+[^\s]+\s+import\s+[^\s]+|import\s+[^\s]+)'

    # Find all import statements in the function code
    imports = re.findall(import_re, func_code, re.MULTILINE)

    for import_statement in imports:
        print("Import statement of functions:", import_statement, end='\n\n\n')
        try:
            exec(import_statement)
        except Exception as e:
            print(f"Failed to import: {import_statement}. Error: {e}")

def initialize_functions():
    functions = fetch_python_functions()
    for _, func_code in functions:
        # Extract and run import statements
        extract_and_run_imports(func_code)    
        
        # Then execute the function code
        try:
            exec(func_code, globals())
            # if _ in globals():
            #     print(f"Function {_} is loaded. it's code is: {func_code}")
            # else:
            #     print(f"Function {_} is not loaded.")    
        except Exception as e:
            print(f"Failed to execute function code. Error: {e}")

    # Functions are now loaded into the global scope
initialize_functions()

# Load sap_credentials (not pushed to github but exposed in cloud foundry until we switch to CF env vars)
# Read the API key from the file
with open('.sap_credentials', 'r') as file:
    sap_api_key = file.read().strip()

# get skills data to build tools
def fetch_skill_details():
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT SKILLNAME, SKILLDESCRIPTION, PARAMETERS FROM SKILLS")
            return cursor.fetchall()
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# App title
st.set_page_config(page_title="Enterprise Assistant", page_icon="💎")

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

# Initialize OpenAI client with the API key from session state
if 'openai_api_key' in st.session_state:
    client = OpenAI(api_key=st.session_state['openai_api_key'])
else:
    client = OpenAI()  # Initialize without an API key

# Check if assistant and thread are already created
if 'assistant_id' not in st.session_state or 'thread_id' not in st.session_state:
    
    skill_details = fetch_skill_details()
    print("Loaded skills: ", skill_details, end='\n\n')
    tools = [{"type": "code_interpreter"}]  # Starting with the code interpreter tool

    for skill_name, skill_description, parameters in skill_details:
        try:
            # Load parameters if not empty, else set to empty dict
            parameters_data = json.loads(parameters) if parameters.strip() else {}
        except json.JSONDecodeError:
            # Fallback to empty dict if JSON parsing fails
            parameters_data = {}

        tool = {
            "type": "function",
            "function": {
                "name": skill_name,
                "description": skill_description,
                "parameters": parameters_data
            }}
        tools.append(tool)

    print("Loaded tools: ", tools, end='\n\n')

    # Create an assistant and a thread
    assistant = client.beta.assistants.create(
        name="Streamlit Jewel",
        instructions="You are a helpful assistant running within enterprise software. Answer to the best of your knowledge, be truthful if you don't know. Concise answers, no harmful language or unethical replies.",
        tools=tools,
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

# 
def wait_on_run(run, thread_id):
    while run.status in ["queued", "in_progress"]:
        print("Run status: ", run.status, end='\n\n')
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        time.sleep(0.2)

        if run.status == "requires_action":
            tools_to_call = run.required_action.submit_tool_outputs.tool_calls
            tool_output_array = []
            for tool in tools_to_call:
                tool_call_id = tool.id
                function_name = tool.function.name
                print("Selected tools: ", function_name, end='\n\n')
                print("Tools arguments: ", json.loads(tool.function.arguments), end='\n\n\n')

            # Call the appropriate function dynamically based on the function name
            import types

            # Iterate over all items in the global namespace
            for name, obj in globals().items():
                # Check if the object is a function
                if isinstance(obj, types.FunctionType):
                    print(name)
        
            function_to_call = globals().get(function_name)
            print("Function as string: ", function_to_call , end='\n\n\n')

            if function_to_call:
                # Check if the function expects the SAP API key
                if 'sap_api_key' in function_to_call.__code__.co_varnames:
                    # Check if tool function arguments are not empty
                    if tool.function.arguments:
                        function_args = json.loads(tool.function.arguments)
                        # If the function requires the SAP API key and has additional arguments
                        output = function_to_call(sap_api_key, **function_args)
                        print("Output with sap key and tool arguments: ", output , end='\n\n\n')
                    else:
                        # If the function requires only the SAP API key
                        output = function_to_call(sap_api_key)
                        print("Output with just sap api key: ", output , end='\n\n\n')

                else:
                    # If the function does not require the SAP API key
                    function_args = json.loads(tool.function.arguments)
                    output = function_to_call(**function_args)
                    print("Output with just tool arguments: ", output , end='\n\n\n')
                
                print(f"Output of {function_name}: ", output, end='\n\n')

            else:
                print(f"Function {function_name} not found.")

                # Ensure the output is a JSON string
                if not isinstance(output, str):
                    output = json.dumps(output)

                if output:
                    tool_output_array.append({"tool_call_id": tool_call_id, "output": output})


            # Submit the tool outputs
            run = client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_output_array
            )

    return run

# User-provided prompt
if prompt := st.chat_input(disabled=not openai_api_key):

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