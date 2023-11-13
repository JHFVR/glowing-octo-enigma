# glowing-octo-enigma
Chatbot tests with OpenAI's new assistant API

## Setup dotenv
(this is now done directly in the side bar)

Install python-dotenv and create a file called ".env" in your working directory. The file should contain one line with:
OPENAI_API_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

## Run app locally
streamlit run streamlit_app.py

## Deploy do Cloud Foundry
works with the specs and manifest as in the repo. CF only accepts python 3.11 right now and you need to create a Procfile to overwrite the manifest and land the start command.....