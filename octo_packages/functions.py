import json
import requests

def get_current_weather(location, unit="fahrenheit"):
    """Get the current weather in a given location"""
    if "tokyo" in location.lower():
        return json.dumps({"location": "Tokyo", "temperature": "10", "unit": "celsius"})
    elif "san francisco" in location.lower():
        return json.dumps({"location": "San Francisco", "temperature": "72", "unit": "fahrenheit"})
    elif "paris" in location.lower():
        return json.dumps({"location": "Paris", "temperature": "22", "unit": "celsius"})
    else:
        return json.dumps({"location": location, "temperature": "unknown"})
    
import requests

def get_fieldglass_approvals(sap_api_key):
    """
    Function to send a GET request to the SAP Fieldglass API for approvals.
    The API key is read from a file named '.sap_credentials'.
    
    :return: A response object from the requests module.
    """

    # Endpoint URL
    url = "https://sandbox.api.sap.com/fieldglass/api/v1/approvals"

    # Headers
    headers = {
        "APIKey": sap_api_key,
        "Accept": "application/json"
    }

    # Sending the GET request
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Return the JSON response as a string
        return response.json()
    else:
        # Handle errors or unsuccessful responses
        return {"error": f"Request failed with status code {response.status_code}"}


