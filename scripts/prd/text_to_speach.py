import requests
import os
from dotenv import load_dotenv

def generate_and_save_audio(
    text,
    foldername,
    filename,
    voice_id,
    elevenlabs_apikey,
    model_id="eleven_multilingual_v2",
    stability=0.4,
    similarity_boost=0.80,
    output_format="mp3"
):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": f"audio/{output_format}",
        "Content-Type": "application/json",
        "xi-api-key": elevenlabs_apikey
    }

    data = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost
        }
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return False
    else:
        os.makedirs(foldername, exist_ok=True)
        file_path = os.path.join(foldername, f"{filename}.{output_format}")
        with open(file_path, 'wb') as f:
            f.write(response.content)
        print(f"Audio saved to {file_path}")
        return True

if __name__ == "__main__":
    import argparse

    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate speech audio using ElevenLabs API.")
    parser.add_argument("--text", type=str, required=True, help="Text to convert to speech.")
    parser.add_argument("--folder", type=str, default="output_audio", help="Output folder.")
    parser.add_argument("--filename", type=str, default="output", help="Output filename (without extension).")
    parser.add_argument("--voice_id", type=str, required=True, help="ElevenLabs voice ID.")
    parser.add_argument("--model_id", type=str, default="eleven_multilingual_v2", help="Model ID.")
    parser.add_argument("--stability", type=float, default=0.4, help="Voice stability (0.0-1.0).")
    parser.add_argument("--similarity_boost", type=float, default=0.80, help="Voice similarity boost (0.0-1.0).")
    parser.add_argument("--output_format", type=str, default="mp3", choices=["mp3", "wav"], help="Audio format.")
    parser.add_argument("--api_key", type=str, default=None, help="ElevenLabs API key (or set ELEVENLABS_APIKEY env var).")

    args = parser.parse_args()

    elevenlabs_apikey = args.api_key or os.getenv("ELEVENLABS_APIKEY")
    if not elevenlabs_apikey:
        print("Error: ElevenLabs API key not provided. Set ELEVENLABS_APIKEY env var or use --api_key.")
        exit(1)

    generate_and_save_audio(
        text=args.text,
        foldername=args.folder,
        filename=args.filename,
        voice_id=args.voice_id,
        elevenlabs_apikey=elevenlabs_apikey,
        model_id=args.model_id,
        stability=args.stability,
        similarity_boost=args.similarity_boost,
        output_format=args.output_format
    )


    # python text_to_speach.py --text "Hello world" --voice_id YOUR_VOICE_ID --folder myfolder --filename myaudio