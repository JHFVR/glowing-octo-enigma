from cfenv import AppEnv
from hdbcli import dbapi
from dotenv import load_dotenv
import os
import json 
import requests
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
        print(import_statement)
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
        except Exception as e:
            print(f"Failed to execute function code. Error: {e}")

    # Functions are now loaded into the global scope
initialize_functions()

# import json
# import requests

# def get_current_weather(location, unit="fahrenheit"):
#     """Get the current weather in a given location"""
#     if "tokyo" in location.lower():
#         return json.dumps({"location": "Tokyo", "temperature": "10", "unit": "celsius"})
#     elif "san francisco" in location.lower():
#         return json.dumps({"location": "San Francisco", "temperature": "72", "unit": "fahrenheit"})
#     elif "paris" in location.lower():
#         return json.dumps({"location": "Paris", "temperature": "22", "unit": "celsius"})
#     else:
#         return json.dumps({"location": location, "temperature": "unknown"})
    
# import requests

# def get_fieldglass_approvals(sap_api_key):
#     """
#     Function to send a GET request to the SAP Fieldglass API for approvals.
#     The API key is read from a file named '.sap_credentials'.
    
#     :return: A response object from the requests module.
#     """

#     # Endpoint URL
#     url = "https://sandbox.api.sap.com/fieldglass/api/v1/approvals"

#     # Headers
#     headers = {
#         "APIKey": sap_api_key,
#         "Accept": "application/json"
#     }

#     # Sending the GET request
#     response = requests.get(url, headers=headers)

#     # Check if the request was successful
#     if response.status_code == 200:
#         # Return the JSON response as a string
#         return response.json()
#     else:
#         # Handle errors or unsuccessful responses
#         return {"error": f"Request failed with status code {response.status_code}"}


