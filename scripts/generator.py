import os, random, re
from pathlib import Path
from moviepy.editor import (
    VideoFileClip, concatenate_videoclips, AudioFileClip,
    CompositeAudioClip, CompositeVideoClip, TextClip
)
from gtts import gTTS

# -------------------------------
# Config
# -------------------------------
clips_folder = Path("/Videos")
audio_file = Path("/generated_audio/story_audio.mp3")
output_file = Path("/final_videos/final_video.mp4")
vertical_resolution = (1080, 1920)
fade_duration = 0.5

# -------------------------------
# Step 1: Load or generate audio
# -------------------------------
if not audio_file.exists():
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
# else:
#     # If audio exists, reload story_text for subtitle generation
#     with open(audio_file.with_suffix('.txt'), 'r', encoding='utf-8') as f:
#         story_text = f.read()

narration = AudioFileClip(str(audio_file))
audio_duration = narration.duration

# -------------------------------
# Step 2: Select and resize clips
# -------------------------------
all_videos = [VideoFileClip(str(p)) for p in clips_folder.glob("*.mp4")]
if not all_videos:
    raise Exception("No video files found!")

num_clips = random.randint(5, 10)
selected = random.sample(all_videos, min(num_clips, len(all_videos)))

target_each = audio_duration / len(selected)

processed = []
for clip in selected:
    clip = clip.resize(height=vertical_resolution[1]).crop(
        x_center=clip.w // 2, width=vertical_resolution[0],
        y_center=clip.h // 2, height=vertical_resolution[1]
    ).fadein(fade_duration).fadeout(fade_duration)

    if clip.duration > target_each:
        clip = clip.subclip(0, target_each)
    else:
        clip = clip.fx(lambda c: c.speedx(c.duration / target_each))

    processed.append(clip)

video = concatenate_videoclips(processed, method="compose")

# -------------------------------
# Step 3: Add audio to match length
# -------------------------------
video = video.set_duration(audio_duration).set_audio(narration)

# -------------------------------
# Step 4: Generate subtitles WITHOUT Whisper
# -------------------------------
def split_sentences(text):
    # Split on sentence-ending punctuation followed by a space or end of string
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

sentences = split_sentences(story_text)
n_sentences = len(sentences)
sentence_duration = audio_duration / n_sentences

subtitle_timings = []
for i, sentence in enumerate(sentences):
    start = i * sentence_duration
    end = (i + 1) * sentence_duration
    subtitle_timings.append((start, end, sentence))

# -------------------------------
# Step 5: Karaoke-style text overlay (no Whisper)
# -------------------------------
base_text = " ".join(s for _, _, s in subtitle_timings)
gray_text = TextClip(base_text, fontsize=60, color="gray",
                     method="caption", size=(int(vertical_resolution[0]*0.9), None),
                     align="center", font="Arial-Bold")

clips = [video, gray_text.set_position(("center", "bottom")).set_duration(audio_duration)]

# Animated yellow overlay per sentence
for start, end, sentence in subtitle_timings:
    yellow_text = TextClip(sentence, fontsize=60, color="yellow",
                           method="caption", size=(int(vertical_resolution[0]*0.9), None),
                           align="center", font="Arial-Bold")
    yellow_text = yellow_text.set_start(start).set_end(end).set_position(("center", "bottom"))
    clips.append(yellow_text)

final = CompositeVideoClip(clips)

# -------------------------------
# Step 6: Export final
# -------------------------------
final.write_videofile(
    str(output_file),
    codec="libx264",
    audio_codec="aac",
    fps=30,
    threads=4
)
print(f"✅ Generated: {output_file}")