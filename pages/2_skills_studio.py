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

# Streamlit app
st.title('Skills Data')

# Fetch and display the data
data = fetch_data()
if not data.empty:
    st.dataframe(data)  # Use dataframe for better formatting
else:
    st.write("No data found.")

# Close the database connection
conn.close()
