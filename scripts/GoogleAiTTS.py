import os
import json
import base64
import subprocess
import requests

def generate_tts(
    text="Say cheerfully: Have a wonderful day!",
    api_key="AIzaSyA9p4K8vflnQUKu0l26sk1wJ66d3ZvYg4g",
    model="gemini-2.5-flash-preview-tts",
    voice_name="Orus",
    output_audio_path="/generated_audio/temp_g_ai_tts",
    # output_pcm="g_ai_out",
    # output_wav="g_ai_out",
    convert_to_wav=True
):
    # ✅ Ensure directory exists
    os.makedirs(output_audio_path, exist_ok=True)

    # ✅ Use Windows-safe paths
    pcm_path = os.path.join(output_audio_path, ".pcm")
    wav_path = os.path.join(output_audio_path, ".wav")

    # ✅ Load API key
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("API key must be provided either as argument or via GEMINI_API_KEY environment variable.")

    # ✅ Build request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "contents": [{
            "parts": [{
                "text": text
            }]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice_name
                    }
                }
            }
        },
        "model": model
    }

    # ✅ Send request
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code != 200:
        raise Exception(f"Request failed ({response.status_code}): {response.text}")

    # ✅ Decode response
    data = response.json()
    try:
        audio_base64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    except KeyError:
        raise KeyError("Unexpected response format: couldn't locate base64 audio data in response.")

    # ✅ Write PCM audio
    with open(pcm_path, "wb") as f:
        f.write(base64.b64decode(audio_base64))
    print(f"PCM audio saved to {pcm_path}")

    # ✅ Convert PCM → WAV (optional)
    if convert_to_wav:
        if not os.path.exists(pcm_path) or os.path.getsize(pcm_path) == 0:
            raise RuntimeError(f"PCM file missing or empty: {pcm_path}")
        try:
            subprocess.run([
                "ffmpeg", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", pcm_path, wav_path
            ], check=True, text=True)
            print(f"WAV file saved to {wav_path}")
        except subprocess.CalledProcessError as e:
            print("FFmpeg error output:\n", e.stderr)
            raise RuntimeError("FFmpeg conversion failed. Make sure ffmpeg is installed and in PATH.")

# Example usage
# generate_tts(text="Good morning, have a great day!", voice_name="Kore")


# Male voices
# Voice name	Tone style
# Achird	Friendly and engaging
# Algenib	Deep and gravelly
# Algieba	Smooth and confident
# Alnilam	Firm and authoritative
# Charon	Clear and informative
# Enceladus	Breathy yet grounded
# Fenrir	Excitable and energetic
# Iapetus	Clean and articulate
# Orus	Firm and motivational
# Puck	Upbeat and lively
# Rasalgethi	Commanding and informative
# Sadachbia	Lively and assertive
# Sadaltager	Knowledgeable and trustworthy
# Schedar	Even and calm
# Umbriel	Easy-going and relaxed
# Zubenelgenubi	Casual and natural
# Recommended for motivational YouTube Shorts (Male tone):

# Orus — firm and dynamic; emphasizes clarity and focus.

# Rasalgethi — confident and commanding; gives presence and authority.

# Fenrir — energetic and passionate; ideal for upbeat motivation.

# Female voices
# Voice name	Tone style
# Achernar	Soft and inspiring
# Aoede	Breezy and approachable
# Autonoe	Bright and expressive
# Callirrhoe	Easy-going and trustworthy
# Despina	Smooth and empowered
# Erinome	Clear and articulate
# Gacrux	Mature and thoughtful
# Kore	Firm and professional
# Laomedeia	Upbeat and hopeful
# Leda	Youthful and lively
# Pulcherrima	Confident and forward
# Sulafat	Warm and empathetic
# Vindemiatrix	Gentle and graceful
# Zephyr	Bright and radiant
# Recommended for motivational YouTube Shorts (Female tone):

# Kore — crisp, firm, and authoritative; works perfectly for narration-style motivation.

# Autonoe — bright and emotionally expressive; ideal for storytelling or empathetic inspiration.

# Sulafat — warm and genuine; conveys encouragement effectively.

# For motivational short-form videos, the best pairing for emotional depth and listener engagement:

# Male: Orus or Fenrir

# Female: Kore or Sulafat
