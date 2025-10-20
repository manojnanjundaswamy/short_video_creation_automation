
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
from faster_whisper import WhisperModel

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


extracted_audio_path = os.path.join("/final_videos", "b19ea183-623e-4524-91db-f09c78db6ec8", "final_combined_video.mp4")
os.makedirs(os.path.dirname(extracted_audio_path), exist_ok=True)
wordlevel_info =  extract_word_timestamps(extracted_audio_path)