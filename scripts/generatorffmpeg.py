import os
import random
import re
from pathlib import Path
from gtts import gTTS
import ffmpeg
import subprocess

# -------------------------------
# Config
# -------------------------------
clips_folder = Path("/Videos")
audio_file = Path("/generated_audio/story_audio.mp3")
story_file = audio_file.with_suffix('.txt')
output_file = Path("/final_videos/final_video.mp4")
vertical_resolution = (1080, 1920)
fade_duration = 0.5
srt_file = Path("/generated_audio/subs.srt")

# -------------------------------
# Step 1: Load or generate audio
# -------------------------------
# if not audio_file.exists():
story_text = (
    "I still remember the day my world shifted. My brother and I inherited our father’s shop—a dream we once shared. "
    "But as days passed, I noticed the numbers didn’t add up, and the trust we’d built as children began to fray.\n\n"
    "One stormy night, I discovered the truth. My brother had forged documents, siphoning away the profit and, with one legal twist, "
    "forced me out of the business—out of my own family. With only an old coat and a heart full of pain, I slept beneath the eaves of the village temple, "
    "wondering how everything had changed so fast.\n\n"
    "I found work where I could—sweeping floors, brewing tea, serving kindness to strangers even when I felt empty. Over time, "
    "I scraped together enough to open a tiny stall of my own. I never spoke ill of my brother. Instead, I poured my soul into every cup and every smile, "
    "helping anyone who needed it. People began to notice—and soon, my little tea stall was always full, while my brother’s shop stood empty, haunted by greed and regret.\n\n"
    "Then, one evening, he appeared—humbled, desperate, and broken. He collapsed into a chair at my stall, unable to meet my eyes. "
    "Without hesitation, I placed a warm cup before him and offered shelter. He whispered through tears, “After all I’ve done, why would you help me?” "
    "I looked at him and replied, “Betrayal may have burned our past, but only kindness can plant what comes next.”\n\n"
    "Now, I understand—karma may take its time, but it always returns. Betrayal hurt, but compassion healed. "
    "In the end, it’s not what was taken from me that defines my story, but what I chose to give."
)
gTTS(story_text, lang="en", slow=False).save(str(audio_file))
with open(story_file, "w", encoding="utf-8") as f:
    f.write(story_text)
# else:
#     with open(story_file, "r", encoding="utf-8") as f:
#         story_text = f.read()

# Get audio duration using ffprobe
def get_audio_duration(audio_path):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)

audio_duration = get_audio_duration(audio_file)

# -------------------------------
# Step 2: Select and resize/crop clips
# -------------------------------
# all_videos = list(clips_folder.glob("*.mp4"))
all_videos = [p for p in clips_folder.glob("*.mp4")
              if ffmpeg.probe(str(p))['streams'][0]['width'] >= vertical_resolution[0]
              and ffmpeg.probe(str(p))['streams'][0]['height'] >= vertical_resolution[1]]

if not all_videos:
    raise Exception("No video files found!")

num_clips = random.randint(5, 10)
selected = random.sample(all_videos, min(num_clips, len(all_videos)))
target_each = audio_duration / len(selected)

# -------------------------------
# Step 3: Generate SRT subtitles
# -------------------------------
def split_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

sentences = split_sentences(story_text)
n_sentences = len(sentences)
sentence_duration = audio_duration / n_sentences

def seconds_to_srt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

with open(srt_file, "w", encoding="utf-8") as f:
    for i, sentence in enumerate(sentences):
        start = i * sentence_duration
        end = (i + 1) * sentence_duration
        f.write(f"{i+1}\n{seconds_to_srt_time(start)} --> {seconds_to_srt_time(end)}\n{sentence}\n\n")

# -------------------------------
# Step 4: Run FFmpeg pipeline
# -------------------------------
# Build input streams and process each clip
processed_clips = []
for clip in selected:
    # Build filter chain for each clip
    processed = (
        ffmpeg
        .input(str(clip))
        .filter('scale', -2, vertical_resolution[1])
        .filter('crop', vertical_resolution[0], vertical_resolution[1])
        .filter('fade', type='in', start_time=0, duration=fade_duration)
        .filter('fade', type='out', start_time=target_each-fade_duration, duration=fade_duration)
        .trim(start=0, end=target_each)
        .setpts('PTS-STARTPTS')
    )
    processed_clips.append(processed)

# Concatenate all processed clips
if len(processed_clips) == 1:
    video_stream = processed_clips[0]
else:
    video_stream = ffmpeg.concat(*processed_clips, v=1, a=0)

# Overlay subtitles
video_with_subs = ffmpeg.filter(video_stream, 'subtitles', str(srt_file))

# Add audio
audio = ffmpeg.input(str(audio_file)).audio

# Output
ffmpeg.output(video_with_subs, audio, str(output_file),
              vcodec='libx264', acodec='aac', pix_fmt='yuv420p', shortest=None, r=25).overwrite_output().run()

print(f"✅ Generated: {output_file}")