import requests

from utils import measure_execution_time, logging

@measure_execution_time
def callChatAPI():
    api_url = 'http://localhost:7860/gradio_api/call/generate_tts_audio'

    # Other form fields as per API spec
    data = {
        "text_input": "Hello from local file!", 
        "language_id": "en",
        "exaggeration_input": 0.25,
        "temperature_input": 0.05,
        "seed_num_input": 3,
        "cfgw_input": 0.2
    }

    # Open your local mp3 file in binary mode
    with open(r"/app/generated_audio/cfdc0787-52af-40b5-87f9-e9a3b9a7bad5/1.mp3", "rb") as f:
        files = {
            'audio_prompt_path_input': ('1.mp3', f, 'audio/mpeg')
        }

        response = requests.post(api_url, data=data, files=files)

    logging(response.status_code)
    try:
        logging(response.json())
    except Exception:
        logging(response.text)


callChatAPI()