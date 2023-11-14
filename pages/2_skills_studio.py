import os
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

def hello():
    host, port, user, password = get_db_credentials()
    conn = dbapi.connect(address=host, port=int(port), user=user, password=password)
    cursor = conn.cursor()
    cursor.execute("select CURRENT_UTCTIMESTAMP from DUMMY", {})
    ro = cursor.fetchone()
    cursor.close()
    conn.close()
    return "Current time is: " + str(ro[0])

# Streamlit app
st.title('HANA Cloud Connection Example')
if st.button('Get Current UTC Time'):
    result = hello()
    st.write(result)
