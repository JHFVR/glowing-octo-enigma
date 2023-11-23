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
from datetime import datetime
import logging

# Define a new logging level
CUSTOM_INFO_LEVEL_NUM = 25
logging.addLevelName(CUSTOM_INFO_LEVEL_NUM, "LOGGING")

def custom_logger(self, message, *args, **kws):
    if self.isEnabledFor(CUSTOM_INFO_LEVEL_NUM):
        # Yes, logger takes its '*args' as 'args'.
        self._log(CUSTOM_INFO_LEVEL_NUM, message, args, **kws) 

# Add the new method to Logger class
logging.Logger.custom_logger = custom_logger
logging.basicConfig(level=CUSTOM_INFO_LEVEL_NUM)
logger = logging.getLogger(__name__)

# Load .env file if it exists for local development
load_dotenv()

def get_db_credentials():
    logger.custom_logger("Retrieving database credentials")
    if 'VCAP_SERVICES' in os.environ:
        logger.custom_logger("Running on Cloud Foundry - fetching credentials from VCAP_SERVICES")
        env = AppEnv()
        hana_service = env.get_service(label='hana')
        credentials = hana_service.credentials
        return credentials['host'], credentials['port'], credentials['user'], credentials['password']
    else:
        logger.custom_logger("Running locally - fetching credentials from environment")
        return os.getenv('HANA_HOST'), os.getenv('HANA_PORT'), os.getenv('HANA_USER'), os.getenv('HANA_PASSWORD')

host, port, user, password = get_db_credentials()
try:
    conn = dbapi.connect(address=host, port=int(port), user=user, password=password)
    logger.custom_logger("Successfully connected to the database")
except Exception as e:
    logging.error(f"Failed to connect to the database. Error: {e}")

def fetch_python_functions():
    with conn.cursor() as cursor:
        cursor.execute("SELECT SkillName, PythonFunction FROM Skills")
        return cursor.fetchall()

def extract_and_run_imports(func_code):
    import_re = r'^\s*(from\s+[^\s]+\s+import\s+[^\s]+|import\s+[^\s]+)'
    imports = re.findall(import_re, func_code, re.MULTILINE)

    for import_statement in imports:
        logger.custom_logger(f"Executing import statement: {import_statement}")
        try:
            exec(import_statement)
        except Exception as e:
            logging.error(f"Failed to import: {import_statement}. Error: {e}")

def initialize_functions():
    functions = fetch_python_functions()
    for _, func_code in functions:
        extract_and_run_imports(func_code)    
        try:
            exec(func_code, globals())
        except Exception as e:
            logging.error(f"Failed to execute function code. Error: {e}")

# Functions are now loaded into the global scope
initialize_functions()

# Load sap_credentials (not pushed to github but exposed in cloud foundry until we switch to CF env vars)
# Read the API key from the file
try:
    with open('.sap_credentials', 'r') as file:
        sap_api_key = file.read().strip()
    logger.custom_logger("SAP API key loaded successfully")
except Exception as e:
    logging.error(f"Error loading SAP API key: {e}")

def fetch_skill_details():
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT SKILLNAME, SKILLDESCRIPTION, PARAMETERS FROM SKILLS")
            return cursor.fetchall()
    except Exception as e:
        logging.error(f"An error occurred while fetching skill details: {e}")
        return []

# App title
st.set_page_config(page_title="Enterprise Assistant", page_icon="💎")

# Start of the Streamlit sidebar
with st.sidebar:
    # Streamlit UI setup for title
    st.markdown("""
        <h1 style="text-align: center">
        <strong>S</strong>oftware <strong>A</strong>musement <strong>P</strong>ark<br><br> 
        <img src="https://raw.githubusercontent.com/JHFVR/jle/main/jle_blue.svg" width="50px" height="50px" /> <br><br>
        </h1>
        """, unsafe_allow_html=True)

    # Check if running in a Cloud Foundry environment
    if 'VCAP_SERVICES' in os.environ or 'VCAP_APPLICATION' in os.environ:
        logger.custom_logger("Running in a Cloud Foundry environment")
        if 'openai_api_key' in st.session_state:
            st.success('OpenAI API key already provided!', icon='✅')
        else:
            openai_api_key = st.text_input('Enter OpenAI API key:', type='password')
            if openai_api_key:
                st.session_state.openai_api_key = openai_api_key
                st.success('API key stored in session for Cloud Foundry. Proceed to chat!', icon='👉')
            else:
                st.warning('Please enter your API key!', icon='⚠️')
    else:
        logger.custom_logger("Running in a non-Cloud Foundry environment")
        if 'OPENAI_API_KEY' in os.environ:
            st.success('OpenAI API key already provided!', icon='✅')
            openai_api_key = os.environ['OPENAI_API_KEY']
            st.session_state.openai_api_key = openai_api_key
        else:
            openai_api_key = st.text_input('Enter OpenAI API key:', type='password')
            if not openai_api_key:
                st.warning('Please enter your API key!', icon='⚠️')
            else:
                with open('.env', 'a') as f:
                    f.write(f'OPENAI_API_KEY={openai_api_key}\n')
                st.success('API key stored. Proceed to chat!', icon='👉')

# Initialize OpenAI client with the API key from session state
if 'openai_api_key' in st.session_state:
    client = OpenAI(api_key=st.session_state['openai_api_key'])
    logger.custom_logger("OpenAI client initialized with API key from session state")
else:
    client = OpenAI()  # Initialize without an API key
    logging.warning("OpenAI client initialized without an API key")

# Check if assistant and thread are already created
if 'assistant_id' not in st.session_state or 'thread_id' not in st.session_state:
    
    skill_details = fetch_skill_details()
    logger.custom_logger(f"Loaded skills: {skill_details}")

    tools = [{"type": "code_interpreter"}]  # Starting with the code interpreter tool

    for skill_name, skill_description, parameters in skill_details:
        try:
            # Load parameters if not empty, else set to empty dict
            parameters_data = json.loads(parameters) if parameters.strip() else {}
        except json.JSONDecodeError as e:
            # Fallback to empty dict if JSON parsing fails
            logging.error(f"JSON decoding error for parameters of {skill_name}: {e}")
            parameters_data = {}

        tool = {
            "type": "function",
            "function": {
                "name": skill_name,
                "description": skill_description,
                "parameters": parameters_data
            }}
        tools.append(tool)

    logger.custom_logger(f"Loaded tools: {tools}")

    try:
        # Create an assistant and a thread
        assistant = client.beta.assistants.create(
            name="Streamlit Jewel",
            instructions="Your name is Jewel. You are a second brain and a helpful assistant running within enterprise software. A person will ask you a question and you will provide a helpful answer. Write the answer in the same language as the question. If you don't know the answer, just say that you don't know. Don't try to make up an answer. Concise answers, no harmful language or unethical replies.",
            tools=tools,
            model="gpt-4-1106-preview"
        )
        thread = client.beta.threads.create()

        # Store the IDs in session state
        st.session_state.assistant_id = assistant.id
        st.session_state.thread_id = thread.id
    except Exception as e:
        logging.error(f"Error creating assistant or thread: {e}")
else:
    # Use existing IDs
    assistant_id = st.session_state.assistant_id
    thread_id = st.session_state.thread_id

def display_messages(thread_id):
        try:
            
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
        except Exception as e:
            logging.error(f"Error displaying messages: {e}")
            
# Display an initial greeting message
if 'initialized' not in st.session_state:
    with st.chat_message("assistant", avatar='https://raw.githubusercontent.com/JHFVR/jle/main/jle_blue.svg'):
        st.write("Hi - how may I assist you today?")
    st.session_state.initialized = False

def wait_on_run(run, thread_id):


    while run.status in ["queued", "in_progress"]:
        # Log the run status with current timestamp
        # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # st.info(f"Run status: {run.status} at {timestamp}")

        # logger.custom_logger(f"Run status: {run.status} at {timestamp}")
        # print("heres the status", run.status[:10])

        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

        if run.status == "requires_action":
            tools_to_call = run.required_action.submit_tool_outputs.tool_calls
            tool_output_array = []

            for tool in tools_to_call:
                tool_call_id = tool.id
                function_name = tool.function.name
                logger.custom_logger(f"Selected tool: {function_name}")
                logger.custom_logger(f"Tool arguments: {json.loads(tool.function.arguments)}")

                function_to_call = globals().get(function_name)
                logger.custom_logger(f"Function as string: {function_to_call}")

                # Initialize output
                output = None

                if function_to_call:
                    try:
                        function_args = json.loads(tool.function.arguments) if tool.function.arguments else {}
                        logger.custom_logger(f"Function arguments: {function_args}")
                        
                        if 'sap_api_key' in function_to_call.__code__.co_varnames:
                            output = function_to_call(sap_api_key, **function_args)
                        else:
                            output = function_to_call(**function_args)
                    except Exception as e:
                        logging.error(f"Error executing {function_name}: {e}")
                        output = {"error": str(e)}

                    logger.custom_logger(f"Output of {function_name}")

                # else:
                #     logging.warning(f"Function {function_name} not found")
                #     output = {"error": f"Function {function_name} not found"}

                # Ensure the output is a JSON string
                if not isinstance(output, str):
                    output = json.dumps(output)

                # Append the output to the tool_output_array
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