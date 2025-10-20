# Install dependencies

import os
from pathlib import Path
import requests
import json
import uuid
import time
from io import BytesIO
from PIL import Image
import numpy as np
import cv2
import psutil
# from faster_whisper import WhisperModel
import whisper

from utils import measure_execution_time, logging


from moviepy.editor import (
    AudioFileClip, concatenate_audioclips, ImageClip, CompositeVideoClip,
    TextClip, VideoFileClip, concatenate_videoclips
)

import ffmpeg  # for audio extraction

import logging

from GoogleAiTTS import generate_tts 

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("/scripts/app_metrics.log"),
#         logging.StreamHandler()
#     ]
# )

# start_time_main = time.time()
# # 🧮 Helper: Measure execution time
# def measure_execution_time(func):
#     """Decorator to measure and log execution time of a function"""
#     def wrapper(*args, **kwargs):
#         start_time = time.time()
#         process = psutil.Process(os.getpid())
#         memory_before = process.memory_info().rss / (1024 * 1024)  # MB
        
#         logging.info(f"▶️ Starting '{func.__name__}' ... Memory: {memory_before:.2f} MB")
#         try:
#             result = func(*args, **kwargs)
#         except Exception as e:
#             logging.error(f"❌ Error occurred in '{func.__name__}': {e}", exc_info=True)
#             raise

#         end_time = time.time()
#         elapsed = end_time - start_time
#         memory_after = process.memory_info().rss / (1024 * 1024)

#         logging.info(
#             f"✅ Finished '{func.__name__}' | Time: {elapsed:.2f}s | "
#             f"Memory Change: {memory_after - memory_before:.2f} MB | Total Memory: {memory_after:.2f} MB"
#         )
#         return result
#     return wrapper


# === User parameters ===
OPENAI_API_KEY = "your-openai-api-key"
PEXELS_API_KEY = "d3O5RKoi56lDxKv3QPDQHE0hqX5XRnwLOVVa6iY4EFQjam5VE8WAPyF1"
ELEVENLABS_API_KEY = "sk_e06fa71475ece8a8e1c428d3ada382c9ebc4f61bc4179774"
ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Example: "Adam" US English voice
VIDEO_TOPIC = " "
NUM_SEGMENTS = 8
VIDEO_LENGTH_SECONDS = 200  # approx
OLLAMA_URL = "http://host.docker.internal:11434/api/generate"

IMAGE_SAVE_FOLDER = Path("/final_videos") 
AUDIO_SAVE_FOLDER = Path("/generated_audio") 

AUDIO_EXTENSION = ".mp3"


# === Helpers ===
@measure_execution_time
def generate_script_and_descriptions(topic, goal, model="llama3.1:8b"):
    # prompt = (f"You are an expert short-form video script writer for Instagram Reels and YouTube Shorts. "
    #           f"Create a script about '{topic}'. The total length is around {VIDEO_LENGTH_SECONDS} seconds, split into {num_segments} concise segments. "
    #           f"Each segment should have a text part and a description of an image to use. "
    #           f"Output a JSON array with each element having 'text' and 'image_description' keys. "
    #           f"Example: [{{'text': '...', 'image_description': '...'}}, ...]")
    prompt_prefix = f"""You are tasked with creating a script for {topic} video that is about {VIDEO_LENGTH_SECONDS} seconds.
    Your goal is to {goal}.
    Please follow these instructions to create an engaging and impactful video:
    1. Begin by setting the scene and capturing the viewer's attention with a captivating visual.
    2. Each scene cut should occur every 5-10 seconds, ensuring a smooth flow and transition throughout the video.
    3. For each scene cut, provide a detailed description of the stock image being shown, which will be used to search Pexels api for free images.
    4. Along with each image description, include a corresponding text that complements and enhances the visual. The text should be concise and powerful.
    5. Make sure the story makes sense and is easy to follow, with a clear beginning, middle, and end.
    6. Ensure that the sequence of images and text builds excitement and encourages viewers to take action.
    7. Strictly output your response in a JSON list format, adhering to the following sample structure:"""

    sample_output = """
    [
        { "image_description": "Description of the first image here.", "text": "Text accompanying the first scene cut." },
        { "image_description": "Description of the second image here.", "text": "Text accompanying the second scene cut." },
        ...
    ]"""

    prompt_postinstruction = f"""By following these instructions, you will create an impactful {topic} short-form video.
    Output:"""

    prompt = prompt_prefix + sample_output + prompt_postinstruction
    logging.info(f"Prompt:\n{prompt}")

    # logging.info("Prompt:")
    # logging.info(prompt)
    headers = {
        "Content-Type": "application/json"
        # "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    # data = {
    #     "model": "gpt-4o-mini",
    #     "messages": [{"role":"system","content":You are a helpful assistant."},
    #                  {"role":"user","content": prompt}],
    #     "max_tokens": max_tokens,
    #     "temperature": 0.7,
    #     "n": 1
    # }
    # response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    # response.raise_for_status()
    # content = response.json()["choices"][0]["message"]["content"]
    
    # Define the JSON schema for the expected output
    format_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "image_description": {"type": "string"},
                "text": {"type": "string"}
            },
            "required": ["image_description", "text"]
        }
    }
    # Optional: Ollama generation options
    options = {
        # "temperature": 0.8,
        # "top_k": 20,
        # "top_p": 0.9,
        # "repeat_penalty": 1.2,
        # "presence_penalty": 1.5,
        # "frequency_penalty": 1.0,
        # "stop": ["\n", "user:"],
        # "num_predict": 512
    }

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": format_schema,
        "options": options
    }
    response = requests.post(OLLAMA_URL, json=payload)
    # logging.info("Ollama response :")
    # logging.info(response)

    response_json = response.json()
    content = response_json.get("response", "").strip()

    logging.info("Ollama response :")
    logging.info(response)

    if response.status_code != 200:
        logging.info("Error:", response.status_code, response.text)
        return [], []

    try:
        output = json.loads(content)
        # logging.info(output)
        image_prompts = [k['image_description'] for k in output]
        texts = [k['text'] for k in output]
        return image_prompts, texts
    except Exception as e:
        logging.info("Failed to parse JSON from Ollama response:", e)
        logging.info("Raw content:", content)
        return [], []
    
    # Try to parse JSON in openAI response robustly
    try:
        script_data = json.loads(content)
    except Exception:
        start = content.find("[")
        end = content.rfind("]") + 1
        script_data = json.loads(content[start:end])
    return script_data

    

@measure_execution_time
def fetch_image_pexels(query, save_path):
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 1, "orientation": "portrait", "size": "medium"}
    
    response = requests.get(url, headers=headers, params=params)
    logging.info("Pexels response status:")
    logging.info(response)
    if response.status_code != 200:
        raise Exception(f"Pexels API error: {response.status_code} {response.text}")
    
    data = response.json()
    if data["total_results"] == 0:
        raise Exception(f"No images found for query: {query}")
    
    image_url = data["photos"][0]["src"]["original"]
    img_data = requests.get(image_url).content
    with open(save_path, "wb") as f:
        f.write(img_data)

@measure_execution_time
def generate_audio_elevenlabs(text, filename):
    filename = os.path.join(filename, f"{i}.mp3")
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.8}
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        with open(filename, "wb") as f:
            f.write(response.content)
    else:
        raise Exception(f"ElevenLabs TTS error {response.status_code}: {response.text}")

@measure_execution_time
def create_video(image_folder, audio_folder, output_file, fps=24, out_res=(1080, 1920)):
    image_files = sorted([f for f in os.listdir(image_folder) if f.endswith('.jpg')], key=lambda x: int(x.split('.')[0]))
    audio_files = sorted([f for f in os.listdir(audio_folder) if f.endswith(AUDIO_EXTENSION)], key=lambda x: int(x.split('.')[0]))
    
    video_clips = []
    audio_clips = []
    
    for img_file, aud_file in zip(image_files, audio_files):
        audio_path = os.path.join(audio_folder, aud_file)
        image_path = os.path.join(image_folder, img_file)
        
        audio_clip = AudioFileClip(audio_path)
        audio_clips.append(audio_clip)
        
        img = cv2.imread(image_path)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        img_1080 = cv2.resize(img_rgb, (1080, 1920))
        blurred_bg = cv2.GaussianBlur(img_rgb, (51, 51), 0)
        blurred_bg = cv2.resize(blurred_bg, out_res)
        
        y_offset = (out_res[1] - 1920) // 2
        blurred_bg[y_offset:y_offset+ 1920, :] = img_1080
        
        clip = ImageClip(blurred_bg).set_duration(audio_clip.duration)
        video_clips.append(clip)
        
    final_audio = concatenate_audioclips(audio_clips)
    final_video = concatenate_videoclips(video_clips, method="compose").set_audio(final_audio)
    
    final_video.write_videofile(output_file, fps=fps, codec="libx264", audio_codec="aac")

# Alternative: Create video from existing video clips and audios
@measure_execution_time
def create_video_from_videos(video_folder, audio_folder, output_file, fps=24, out_res=(1080, 1920)): #TODO: test this function
    # Sorted lists of video and audio files by numeric prefix
    video_files = sorted([f for f in os.listdir(video_folder) if f.endswith('.mp4')], key=lambda x: int(x.split('.')[0]))
    audio_files = sorted([f for f in os.listdir(audio_folder) if f.endswith('.mp3')], key=lambda x: int(x.split('.')[0]))
    
    video_clips = []
    audio_clips = []
    
    for vid_file, aud_file in zip(video_files, audio_files):
        video_path = os.path.join(video_folder, vid_file)
        audio_path = os.path.join(audio_folder, aud_file)
        
        # Load audio clip
        audio_clip = AudioFileClip(audio_path)
        audio_clips.append(audio_clip)
        
        # Load video clip
        vid_clip = VideoFileClip(video_path)
        
        # Resize video keeping aspect ratio, then crop or pad to output resolution
        vid_resized = vid_clip.resize(height=out_res[1])
        
        # If the width after resizing differs, add black bars (letterboxing/pillarboxing)
        if vid_resized.w != out_res[0]:
            # Center video on black background with output resolution
            vid_resized = vid_resized.on_color(
                size=out_res,
                color=(0, 0, 0),
                pos=('center', 'center')
            )
        
        # Set video clip duration exactly to audio clip duration for sync
        clip = vid_resized.set_duration(audio_clip.duration).set_fps(fps)
        
        video_clips.append(clip)
    
    # Combine all audio clips sequentially
    final_audio = concatenate_audioclips(audio_clips)
    # Combine all video clips sequentially (compose in case of different sizes)
    final_video = concatenate_videoclips(video_clips, method="compose").set_audio(final_audio)
    
    # Write final combined video to file
    final_video.write_videofile(output_file, fps=fps, codec="libx264", audio_codec="aac")


# === ElevenLabs Speech-to-Text (STT) integration ===
@measure_execution_time
def upload_audio_for_transcription(audio_filepath):
    url = "https://api.elevenlabs.io/v1/speech-to-text"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
    }
    with open(audio_filepath, "rb") as audio_file:
        files = {
            "file": (os.path.basename(audio_filepath), audio_file, "audio/mpeg")
        }
        response = requests.post(url, headers=headers, files=files)
        logging.info(f"upload_audio_for_transcription response: {response.json()}")
    # response.raise_for_status()
    resp_json = response.json()
    return resp_json["transcription_id"]

@measure_execution_time
def poll_transcription(transcription_id, max_retries=15, wait_seconds=5):
    url = f"https://api.elevenlabs.io/v1/speech-to-text/transcripts/{transcription_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
    }
    for i in range(max_retries):
        response = requests.get(url, headers=headers)
        logging.info(f"poll_transcription response: {response.json()}")
        if response.status_code != 200:
            raise Exception(f"Transcription status error {response.status_code}: {response.text}")
        data = response.json()
        if "text" in data:
            if data.get("status", "completed") == "completed" or "words" in data:
                return data
        time.sleep(wait_seconds)
    raise TimeoutError("Transcription not completed within expected time.")


def add_captions_elevenlabs(video_file, transcript_json, output_file):
    words = transcript_json["words"]
    video = VideoFileClip(video_file)
    
    def make_text_clip(word_text, start, end):
        return (TextClip(word_text, fontsize=40, font="Nimbus-Sans-Bold", color="white",
                         stroke_color="black", stroke_width=2)
                .set_position("center")
                .set_start(start)
                .set_duration(end - start))
    
    text_clips = [make_text_clip(w["text"], w["start"], w["end"]) for w in words]
    final_video = CompositeVideoClip([video, *text_clips])
    final_video.write_videofile(output_file, codec="libx264", audio_codec="aac")

@measure_execution_time
def extract_word_timestamps(audiofilepath):

    model_size = "medium"
    model = WhisperModel(model_size)

    segments, info = model.transcribe(audiofilepath, word_timestamps=True)

    wordlevel_info = []
    for segment in segments:
        for word in segment.words:
            wordlevel_info.append({'word': word.word, 'start': word.start, 'end': word.end})
    return wordlevel_info

# Function to generate text clips
@measure_execution_time
def generate_text_clip(word, start, end, video):
    txt_clip = (TextClip(word,fontsize=80,color='white',font = "DejaVu-Sans-Bold",stroke_width=3, stroke_color='black').set_position('center')
               .set_duration(end - start))

    return txt_clip.set_start(start)


# Function to add captions to video
@measure_execution_time
def add_captions_to_video(videofilename,wordlevelcaptions):
  # Load the video file
  video = VideoFileClip(videofilename)

  # Generate a list of text clips based on timestamps
  clips = [generate_text_clip(item['word'], item['start'], item['end'], video) for item in wordlevelcaptions]

  # Overlay the text clips on the video
  final_video = CompositeVideoClip([video] + clips)

  path, old_filename = os.path.split(videofilename)

  finalvideoname = path+"/"+"final.mp4"
  os.makedirs(os.path.dirname(finalvideoname), exist_ok=True)
  # Write the result to a file
  final_video.write_videofile(finalvideoname, codec="libx264",audio_codec="aac")

  return finalvideoname
    

# === Main Execution Pipeline ===

# Setup workspace folder

# workspace_folder = str(uuid.uuid4()) # TODO: uncomment
workspace_folder = "55508c68-299d-4038-9d8a-b52d5abdb9f7"  # for testing
os.makedirs(IMAGE_SAVE_FOLDER, exist_ok=True)

# logging.info(f"------------------------ New Process started with path: {workspace_folder} ------------------------")
# # logging.info(f"Workspace folder created: {workspace_folder}")

# # Generate script and image prompts
# logging.info("Step 1: Generating script and image prompts via OpenAI...")
# script_data = generate_script_and_descriptions(VIDEO_TOPIC, VIDEO_GOAL, "llama3.1:8b")
# image_prompts, texts = script_data  # unpack the tuple

# logging.info("Final Data:")
# for i, (image_prompt, text) in enumerate(zip(image_prompts, texts), start=1):
#     logging.info(f"Text {i}: {text}")
#     logging.info(f"Image Prompt {i}: {image_prompt}")



# # Fetch images from Pexels
# logging.info("\nStep 2: Fetching images from Pexels...")
# for i, (image_prompt, text) in enumerate(zip(image_prompts, texts), start=1):
#     image_path = os.path.join(IMAGE_SAVE_FOLDER, workspace_folder, f"{i}.jpg")
#     os.makedirs(os.path.dirname(image_path), exist_ok=True)
#     try:
#         fetch_image_pexels(image_prompt, image_path)
#         logging.info(f"Image {i} downloaded: {image_path}")
#     except Exception as e:
#         logging.info(f"Failed to fetch image for segment {i}: {e}")

# # Generate audio clips using ElevenLabs
# # logging.info("\nStep 3: Generating audio clips with ElevenLabs TTS...")
# # for i, seg in enumerate(script_data, start=1):
# #     audio_path = os.path.join(workspace_folder, f"{i}.mp3")
# #     generate_audio_elevenlabs(seg[0], audio_path)
# #     logging.info(f"Audio {i} generated.")
# logging.info("\nStep 3: Generating audio clips with ElevenLabs TTS...")
# for i, text in enumerate(texts, start=1):
#     # audio_path = os.path.join(AUDIO_SAVE_FOLDER, workspace_folder, f"{i}.mp3")
#     audio_path = os.path.join(AUDIO_SAVE_FOLDER, workspace_folder, f"{i}")
#     os.makedirs(os.path.dirname(audio_path), exist_ok=True)
#     # generate_audio_elevenlabs(text, audio_path)
#     generate_tts(
#         text=text, output_audio_path=audio_path )
#     logging.info(f"Audio {i} generated.")    

# # Create combined video with blurred BG and centered images
# logging.info("\nStep 4: Creating combined video...")
# # tempFolderName = "1dd6390d-5d2c-4304-a735-78f61c05cdf0"


combined_video_path = os.path.join(IMAGE_SAVE_FOLDER, workspace_folder, "combined_video.mp4")
os.makedirs(os.path.dirname(combined_video_path), exist_ok=True)
image_folder = os.path.join(IMAGE_SAVE_FOLDER, workspace_folder)
audio_folder = os.path.join(AUDIO_SAVE_FOLDER, workspace_folder)
os.makedirs(os.path.dirname(audio_folder), exist_ok=True)
create_video(image_folder, audio_folder, combined_video_path) #TODO: uncomment
logging.info(f"Combined video saved at: {combined_video_path}")

# Extract audio from video for transcription
try:
    extracted_audio_path = combined_video_path.replace(".mp4", ".mp3")
    logging.info("\nExtracting audio from video for transcription from "+ combined_video_path) #TODO: uncomment
    input_stream = ffmpeg.input(combined_video_path)
    audio_stream = input_stream.audio
    ffmpeg.output(audio_stream, extracted_audio_path).overwrite_output().run()
    logging.info(f"Extracted audio saved at: {extracted_audio_path}")
except ffmpeg.Error as e:
    logging.error(f"Audio extraction failed:\nstdout: {e.stdout.decode()}\nstderr: {e.stderr.decode()}")
except Exception as e:
    logging.info(f"Audio extraction failed: {e}")


wordlevel_info =  extract_word_timestamps(extracted_audio_path)
logging.info("wordlevel_info:::")
logging.info(wordlevel_info)
#create video with subtitles
final_video_path = os.path.join(IMAGE_SAVE_FOLDER, workspace_folder, "final_video_with_captions.mp4")
# generate_final_video(image_folder, wordlevel_info, extracted_audio_path, final_video_path)
video = VideoFileClip(combined_video_path)
add_captions_to_video(combined_video_path,wordlevel_info)

end_time = time.time()
elapsed = end_time - start_time_main

logging.info(f"\nTotal process completed in {elapsed:.2f} seconds. Workspace: {workspace_folder}")




