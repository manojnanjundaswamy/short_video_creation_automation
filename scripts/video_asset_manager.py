"""
video_asset_manager.py

A modular video asset manager for automated Shorts pipelines.

Features:
- Search & download clips from multiple free APIs (Pexels, Pixabay)
- Filter by vertical orientation (or crop/resize to vertical)
- Caching & deduplication (by content SHA1)
- Return local file paths ready for pipeline
- Auto thumbnail generation (PIL)
- Branding: watermark overlay using MoviePy
- Audio mastering: normalization and simple noise reduction (pydub)
- Random B-roll injection and random video/audio effects to make re-uploads unique

Drop this file into your /data/scripts folder and run functions from your pipeline.

Dependencies:
  pip install requests moviepy pydub python-dotenv pillow tqdm ffmpeg-python imagehash

Requires ffmpeg installed in container (apk add ffmpeg) and API keys in env:
  PEXELS_API_KEY, PIXABAY_API_KEY

"""

import os
import io
import hashlib
import random
import time
import json
from pathlib import Path
from typing import List, Tuple, Optional
import requests
from PIL import Image, ImageDraw, ImageFont
from moviepy  import (
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips,
    CompositeVideoClip,
    ImageClip,
    afx,
)
# from pydub import AudioSegment, effects
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = "d3O5RKoi56lDxKv3QPDQHE0hqX5XRnwLOVVa6iY4EFQjam5VE8WAPyF1" #os.getenv("PEXELS_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

# Folders (container paths)
ROOT = Path("/Videos")
VIDEOS = ROOT

VIDEOS.mkdir(parents=True, exist_ok=True)


# ----------------------- utilities -----------------------

def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# def already_have(hashval: str) -> Optional[dict]:
#     for item in DB.get("clips", []):
#         if item.get("sha1") == hashval:
#             return item
#     return None


# ----------------------- API downloaders -----------------------

def search_pexels(query: str, per_page=15):
    if not PEXELS_API_KEY:
        return []
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": per_page}
    r = requests.get(url, headers=headers, params=params, timeout=30)
    if r.status_code != 200:
        return []
    return r.json().get("videos", [])


def search_pixabay(query: str, per_page=15):
    if not PIXABAY_API_KEY:
        return []
    url = "https://pixabay.com/api/videos/"
    params = {"key": PIXABAY_API_KEY, "q": query, "per_page": per_page}
    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200:
        return []
    return r.json().get("hits", [])


def download_url(url: str, out_path: Path) -> bool:
    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        with out_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print("Download failed", e)
        return False


# ----------------------- main fetch function -----------------------

def fetch_clips_for_topic(topic: str, limit: int = 5, prefer_vertical: bool = True) -> List[Path]:
    """Search multiple APIs and download up to `limit` unique clips. Returns list of local file paths."""
    downloaded = []
    # try Pexels first
    vids = search_pexels(topic, per_page=limit * 2)
    for v in vids:
        if len(downloaded) >= limit:
            break
        files = v.get("video_files", [])
        if not files:
            continue
        # prefer vertical or highest res
        candidate = None
        if prefer_vertical:
            for f in files:
                # some Pexels files include width/height
                if f.get("width") and f.get("height") and f["height"] > f["width"]:
                    candidate = f
                    break
        if not candidate:
            candidate = sorted(files, key=lambda x: x.get("height", 0), reverse=True)[0]
        url = candidate.get("link")
        name = f"pexels_{v.get('id')}_{candidate.get('id')}.mp4"
        target = VIDEOS / name
        if target.exists():
            continue
        ok = download_url(url, target)
        if not ok:
            continue
        h = sha1_file(target)
        # dup = already_have(h)
        # if dup:
        #     target.unlink(missing_ok=True)
        #     continue
        # record in DB
        downloaded.append(target)

    # # fallback to Pixabay
    # if len(downloaded) < limit:
    #     hits = search_pixabay(topic, per_page=limit * 2)
    #     for h in hits:
    #         if len(downloaded) >= limit:
    #             break
    #         vidsizes = h.get("videos", {})
    #         items = sorted(list(vidsizes.values()), key=lambda x: x.get("height", 0), reverse=True)
    #         if not items:
    #             continue
    #         chosen = items[0]
    #         url = chosen.get("url")
    #         name = f"pixabay_{h.get('id')}.mp4"
    #         target = VIDEOS / name
    #         if target.exists():
    #             continue
    #         ok = download_url(url, target)
    #         if not ok:
    #             continue
    #         hval = sha1_file(target)
    #         if already_have(hval):
    #             target.unlink(missing_ok=True)
    #             continue
    #         DB["clips"].append({"source": "pixabay", "id": h.get("id"), "url": h.get("pageURL"), "path": str(target), "sha1": hval, "topic": topic, "downloaded_at": time.time()})
    #         save_db()
    #         downloaded.append(target)

    # Final filter: ensure vertical or mark for cropping
    final = []
    for p in downloaded:
        try:
            clip = VideoFileClip(str(p))
            w, h = clip.size
            clip.close()
            if prefer_vertical and h < w:
                # will need cropping later, but still return
                final.append(p)
            else:
                final.append(p)
        except Exception as e:
            print("Invalid clip", p, e)
    return final


# ----------------------- thumbnail generation & branding -----------------------

# def generate_thumbnail(video_path: Path, title: str, out_folder: Path = THUMBS) -> Path:
#     # capture middle frame
#     clip = VideoFileClip(str(video_path))
#     t = clip.duration / 2.0
#     frame = clip.get_frame(t)
#     clip.close()
#     img = Image.fromarray(frame)
#     img = img.resize((1280, 720))

#     draw = ImageDraw.Draw(img)
#     try:
#         font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
#     except Exception:
#         font = ImageFont.load_default()
#     # draw title bottom left
#     margin = 40
#     draw.text((margin, img.height - 120), title, font=font, fill=(255, 255, 255))

#     # apply watermark if available
#     if Path(WATERMARK).exists():
#         mark = Image.open(WATERMARK).convert("RGBA")
#         mark_w = int(img.width * 0.12)
#         mark = mark.resize((mark_w, int(mark.size[1] * (mark_w / mark.size[0]))))
#         img.paste(mark, (img.width - mark_w - 20, img.height - mark.size[1] - 20), mark)

#     out = out_folder / (video_path.stem + "_thumb.jpg")
#     img.save(out, quality=85)
#     return out


# ----------------------- audio mastering -----------------------

# def master_audio(input_audio: Path, output_audio: Path):
#     """Normalize and apply simple noise reduction/filters using pydub."""
#     a = AudioSegment.from_file(str(input_audio))
#     # normalize loudness
#     a = effects.normalize(a)
#     # simple high-pass to reduce rumble
#     a = a.high_pass_filter(100)
#     # export
#     a.export(str(output_audio), format="mp3")
#     return output_audio


# ----------------------- random b-roll injection & effects -----------------------

# def apply_random_video_effect(clip: VideoFileClip) -> VideoFileClip:
#     # randomly apply one or two simple effects
#     opts = ["speed", "mirror", "color"]
#     choice = random.choice(opts)
#     if choice == "speed":
#         factor = random.uniform(0.9, 1.1)
#         try:
#             return clip.fx(afx.speedx, factor)
#         except Exception:
#             return clip
#     elif choice == "mirror":
#         try:
#             return clip.fx(vfx.mirror_x)
#         except Exception:
#             return clip
#     elif choice == "color":
#         try:
#             return clip.fx(vfx.colorx, random.uniform(0.9, 1.2))
#         except Exception:
#             return clip
#     return clip


# def apply_random_audio_effect(audio_path: Path, out_path: Path) -> Path:
#     a = AudioSegment.from_file(str(audio_path))
#     # small pitch shift by changing frame rate
#     if random.random() < 0.4:
#         new_rate = int(a.frame_rate * random.uniform(0.98, 1.02))
#         a = a._spawn(a.raw_data, overrides={"frame_rate": new_rate}).set_frame_rate(a.frame_rate)
#     # random low-volume reverb simulated by overlaying delayed copy
#     if random.random() < 0.3:
#         delayed = a - 8
#         silent = AudioSegment.silent(duration=40)
#         delayed = silent + delayed
#         a = a.overlay(delayed)
#     a = effects.normalize(a)
#     a.export(str(out_path), format="mp3")
#     return out_path


# ----------------------- high level helper -----------------------

def prepare_assets_for_story(topic: str, clips_limit: int = 6) -> dict:
    """Search/download clips, master audio, pick b-roll, generate thumbnail, return paths dict."""
    clips = fetch_clips_for_topic(topic, limit=clips_limit)

    # # master main audio
    # mastered_audio = story_audio.with_name(story_audio.stem + "_master.mp3")
    # master_audio(story_audio, mastered_audio)

    # # create variation of audio to make uniqueness
    # audio_variant = story_audio.with_name(story_audio.stem + "_var.mp3")
    # apply_random_audio_effect(mastered_audio, audio_variant)

    # # pick b-rolls randomly
    # broll = random.sample(list(VIDEOS.glob("*.mp4")), min(3, len(list(VIDEOS.glob("*.mp4")))))

    # # pick watermark if exists
    # watermark = Path(WATERMARK) if Path(WATERMARK).exists() else None

    # generate thumbnail based on first clip
    # thumb = None
    # if clips:
    #     thumb = generate_thumbnail(clips[0], title=topic)

    return {
        "clips": [str(p) for p in clips],
        # "broll": [str(p) for p in broll],
        # "master_audio": str(mastered_audio),
        # "audio_variant": str(audio_variant),
        # "thumbnail": str(thumb) if thumb else None,
        # "watermark": str(watermark) if watermark else None,
    }


# ----------------------- simple CLI for testing -----------------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python video_asset_manager.py <topic>")
        sys.exit(1)
    topic = sys.argv[1]
    # topic = "Dance"
    print("Fetching clips for:", topic)
    out = prepare_assets_for_story(topic, clips_limit=6)
    print(json.dumps(out, indent=2))
