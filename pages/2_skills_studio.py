import os
import pandas as pd
import streamlit as st
from cfenv import AppEnv
from hdbcli import dbapi
from dotenv import load_dotenv
import logging
import python_weather
import asyncio

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
    logger.custom_logger("Fetching database credentials")
    # Check if running on Cloud Foundry
    if 'VCAP_SERVICES' in os.environ:
        logger.custom_logger("Running on Cloud Foundry")
        env = AppEnv()
        hana_service = env.get_service(label='hana')
        credentials = hana_service.credentials
        return credentials['host'], credentials['port'], credentials['user'], credentials['password']
    else:
        logger.custom_logger("Running locally")
        # Load credentials from .env file or environment for local development
        return os.getenv('HANA_HOST'), os.getenv('HANA_PORT'), os.getenv('HANA_USER'), os.getenv('HANA_PASSWORD')

host, port, user, password = get_db_credentials()

try:
    conn = dbapi.connect(address=host, port=int(port), user=user, password=password)
    logger.custom_logger("Database connection established successfully")
except Exception as e:
    logging.error(f"Database connection failed: {e}")

# Fetch data from the database 
def fetch_data():
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM Skills")
            columns = [desc[0] for desc in cursor.description]  # This will capture column names
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)
            return df
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def insert_skill_data(skill_name, skill_description, parameters, python_function):
    try:
        with conn.cursor() as cursor:
            insert_query = """
            INSERT INTO Skills (SkillName, SkillDescription, Parameters, PythonFunction) 
            VALUES (?, ?, ?, ?)
            """
            cursor.execute(insert_query, (skill_name, skill_description, parameters, python_function))
            conn.commit()  # Important to commit the transaction
            logger.custom_logger("Skill added successfully")
            return "Skill added successfully!"
    except Exception as e:
        logging.error(f"Error inserting skill data: {e}")
        return f"An error occurred: {e}"

def delete_skill_data(skill_name):
    try:
        with conn.cursor() as cursor:
            delete_query = "DELETE FROM Skills WHERE SkillName = ?"
            cursor.execute(delete_query, (skill_name,))
            conn.commit()
            logger.custom_logger("Skill deleted successfully")
            return "Skill deleted successfully!"
    except Exception as e:
        logging.error(f"Error deleting skill data: {e}")
        return f"An error occurred: {e}"

def fetch_function_names():
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT SkillName FROM Skills")
            result = cursor.fetchall()
            function_names = [row[0] for row in result]
            return function_names
    except Exception as e:
        logging.error(f"Error fetching function names: {e}")
        return []
    
def update_skills_backup():
    try:
        with conn.cursor() as cursor:
            update_query = """
            INSERT INTO SKILLS_BACKUP
            SELECT * FROM SKILLS
            WHERE SkillID NOT IN (SELECT SkillID FROM SKILLS_BACKUP)
            """
            cursor.execute(update_query)
            conn.commit()
            logger.custom_logger("SKILLS_BACKUP table updated successfully")
            return "SKILLS_BACKUP table updated successfully with new skills."
    except Exception as e:
        logging.error(f"Error updating SKILLS_BACKUP: {e}")
        return f"An error occurred while updating SKILLS_BACKUP: {e}"
    
# Streamlit app
st.title('Find, add and delete skills here')
st.text("")
st.markdown('➡️ Scroll right to see more details of each skill')

# Initialize session state for page tracking (need that to properly refresh the chat box when i switch pages)
if 'current_page' not in st.session_state:
    st.session_state.current_page = None

if 'previous_page' not in st.session_state:
    st.session_state.previous_page = None

# Update the previous page to the current one, and set the current page as "Chat Window"
# if st.session_state.current_page != "skill_studio":
st.session_state.previous_page = st.session_state.current_page
st.session_state.current_page = "skill_studio"

# Fetch and display the data
data = fetch_data()
if not data.empty:
    data = data.iloc[:, 1:]  # Drop the first column
    st.dataframe(data, width=1100)
else:
    st.write("No data found.")

# Add Skill Button and Form
st.text("")
st.markdown('💉 Inject more skills into my brain')

with st.expander("➕ Add Skill"):
    with st.form("add_skill_form"):
        # Skill Name with inline explanation
        skill_name = st.text_input("Skill Name", help="The skills name must be exactly the same as the Python function you will define below.", placeholder="e.g., get_current_weather")

        # Skill Description with inline explanation
        skill_description = st.text_area("Skill Description", help="Describe what this skill does.", placeholder="Get the current weather in a given location")

        # Parameters with inline explanation
        parameters_placeholder = '''{
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"]
                }
            },
            "required": ["location"]
        }
        '''
        parameters = st.text_area("Parameters (JSON Format)", 
                                help="""Define the parameters for this skill in JSON format. If it's just an empty GET request, insert "{\\"type\\": \\"object\\", \\"properties\\": {}}". Type remains object. properties are all fields explicitly mapped in the prompt. Required is enforced.""", 
                                placeholder=parameters_placeholder, 
                                height=330)

        # Python Function with inline explanation
        python_function_placeholder = """def get_current_weather(location, unit=\"fahrenheit\"):
                    \"\"\"Get the current weather in a given location\"\"\"
                    if \"tokyo\" in location.lower():
                        return json.dumps({\"location\": \"Tokyo\", \"temperature\": \"10\", \"unit\": \"celsius\"})
                    elif \"san francisco\" in location.lower():
                        return json.dumps({\"location\": \"San Francisco\", \"temperature\": \"72\", \"unit\": \"fahrenheit\"})
                    elif \"paris\" in location.lower():
                        return json.dumps({\"location\": \"Paris\", \"temperature\": \"22\", \"unit\": \"celsius\"})
                    else:
                        return json.dumps({\"location\": location, \"temperature\": \"unknown\"})"""
        python_function = st.text_area("Python Function", help="Define your python function to call your backend API or agent. If you want to use SAP credentials, simply pass in \"sap_api_key\" as one argument of your function.", placeholder=python_function_placeholder)

        submit_button = st.form_submit_button("Submit")

        if submit_button:
            logger.custom_logger(f"Attempting to add skill: {skill_name}")
            result = insert_skill_data(skill_name, skill_description, parameters, python_function)
            if result.startswith("Skill added successfully"):
                st.success(result)
                backup_update_result = update_skills_backup()
                st.info(backup_update_result)
                logger.custom_logger(f"Skill {skill_name} added and backup updated successfully")
            else:
                st.error(result)
                logging.error(f"Error adding skill {skill_name}: {result}")

# Dropdown for deleting a skill
st.text("")
st.markdown('🪦 Take a skill 6ft under')

function_names = fetch_function_names()
selected_function = st.selectbox("Select a function to delete", function_names)

if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = False

if st.button("Delete Function"):
    st.session_state.confirm_delete = True

if st.session_state.confirm_delete:
    st.write(f"Are you sure you want to delete the function '{selected_function}'?")
    col1, col2 = st.columns(2)
    if col1.button("Yes, delete it"):
        delete_result = delete_skill_data(selected_function)
        st.write(delete_result)
        st.session_state.confirm_delete = False
        logger.custom_logger(f"Function {selected_function} deleted: {delete_result}")
    if col2.button("No, cancel"):
        st.session_state.confirm_delete = False

# Close the database connection
conn.close()
logger.custom_logger("Database connection closed")
