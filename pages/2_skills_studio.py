import os
import pandas as pd
import streamlit as st
from cfenv import AppEnv
from hdbcli import dbapi
from dotenv import load_dotenv

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

# Fetch data from the database 
def fetch_data():
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM Skills")
        columns = [desc[0] for desc in cursor.description]  # This will capture column names
        data = cursor.fetchall()
        df = pd.DataFrame(data, columns=columns)
        return df

def insert_skill_data(skill_name, skill_description, parameters, python_function):
    try:
        with conn.cursor() as cursor:
            insert_query = """
            INSERT INTO Skills (SkillName, SkillDescription, Parameters, PythonFunction) 
            VALUES (?, ?, ?, ?)
            """
            cursor.execute(insert_query, (skill_name, skill_description, parameters, python_function))
            conn.commit()  # Important to commit the transaction
            return "Skill added successfully!"
    except Exception as e:
        return f"An error occurred: {e}"

# Streamlit app
st.title('Skills Data')
st.markdown('➡️ Scroll right to see more details of each skill')

# Fetch and display the data
data = fetch_data()
if not data.empty:
    data = data.iloc[:, 1:]  # Drop the first column
    st.dataframe(data, width=1100)
else:
    st.write("No data found.")

# Add Skill Button and Form
with st.expander("➕ Add Skill"):
    with st.form("add_skill_form"):
        # Skill Name with inline explanation
        st.text_input("Skill Name", help="The skills name must be exactly the same as the Python function you will define below.", placeholder="e.g., get_current_weather")

        # Skill Description with inline explanation
        st.text_area("Skill Description", help="Describe what this skill does.", placeholder="Get the current weather in a given location")

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
        st.text_area("Parameters (JSON Format)", help="Define the parameters for this skill in JSON format. If it's just an empty GET request, insert \"{}\". Type remains object. properties are all fields explictly mapped in the prompt. Required is enforced.", placeholder=parameters_placeholder, height=330)

        # Python Function with inline explanation
        python_function_placeholder = "# Example: def get_current_weather(location, unit):\n#     # Function implementation"
        st.text_area("Python Function", help="Define the parameters for this skill in JSON format.", placeholder=python_function_placeholder)

        submit_button = st.form_submit_button("Submit")

        if submit_button:
            result = insert_skill_data(skill_name, skill_description, parameters, python_function)
            if result.startswith("Skill added successfully"):
                st.success(result)
            else:
                st.error(result)

# Close the database connection
conn.close()