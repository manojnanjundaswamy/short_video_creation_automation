"""
Auto-download free stock videos by topic (Pexels + Pixabay).
Requirements:
  pip install requests moviepy python-dotenv tqdm
  ffmpeg must be installed on system (moviepy uses it).
"""

import os, time, csv, math, sys
import requests
from pathlib import Path
from moviepy import VideoFileClip
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

PEXELS_API_KEY = "d3O5RKoi56lDxKv3QPDQHE0hqX5XRnwLOVVa6iY4EFQjam5VE8WAPyF1"; #os.getenv("PEXELS_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
OUT_DIR = Path("/Videos")
OUT_DIR.mkdir(exist_ok=True)
META_CSV = OUT_DIR / "metadata.csv"

HEADERS = {"Authorization": PEXELS_API_KEY} if PEXELS_API_KEY else {}

# ---------- helpers ----------
def save_metadata_row(row):
    is_new = not META_CSV.exists()
    with open(META_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["source", "id", "url", "local_path", "width", "height", "duration", "license", "tags", "downloaded_at"])
        writer.writerow(row)

def safe_get(url, headers=None, params=None, max_retries=5):
    for attempt in range(max_retries):
        r = requests.get(url, headers=headers, params=params, stream=True, timeout=30)
        if r.status_code == 200:
            return r
        if r.status_code in (429, 503, 502, 500):
            backoff = (2 ** attempt) + (0.5 * attempt)
            print(f"Rate limited or server error {r.status_code}. Backing off {backoff}s...")
            time.sleep(backoff)
            continue
        else:
            print("Request failed:", r.status_code, r.text[:200])
            return None
    return None

# ---------- Pexels ----------
def search_pexels_videos(query, per_page=15, page=1):
    url = "https://api.pexels.com/videos/search"
    params = {"query": query, "per_page": per_page, "page": page}
    r = safe_get(url, headers=HEADERS, params=params)
    if not r: return []
    data = r.json()
    return data.get("videos", [])

def download_url_to_file(url, out_path):
    r = safe_get(url)
    if not r: return False
    total = int(r.headers.get('content-length', 0))
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return True

# ---------- Pixabay ----------
def search_pixabay_videos(query, per_page=20, page=1):
    url = "https://pixabay.com/api/videos/"
    params = {"key": PIXABAY_API_KEY, "q": query, "per_page": per_page, "page": page}
    r = safe_get(url, params=params)
    if not r: return []
    data = r.json()
    return data.get("hits", [])

# ---------- Processing ----------
def crop_to_9_16(input_path, output_path, target_w=1080, target_h=1920):
    try:
        clip = VideoFileClip(str(input_path))
        w, h = clip.size
        # scale to target width then center crop
        scale = target_w / float(w)
        new_h = int(h * scale)
        clip_resized = clip.resize(width=target_w)
        # if new_h < target_h -> scale by height instead
        if new_h < target_h:
            scale = target_h / float(h)
            clip_resized = clip.resize(height=target_h)
        # now crop center
        clip_cropped = clip_resized.fx(lambda c: c.crop(x_center=c.w/2, y_center=c.h/2, width=target_w, height=target_h))
        clip_cropped.write_videofile(str(output_path), codec="libx264", audio_codec="aac", threads=2, verbose=False, logger=None)
        clip.close()
        clip_resized.close()
        clip_cropped.close()
        return True
    except Exception as e:
        print("Crop failed:", e)
        return False

def process_topic(topic, max_download=5):
    print(f"Searching for topic: {topic}")
    downloaded = 0

    # Pexels
    videos = search_pexels_videos(topic, per_page=15)
    for v in videos:
        if downloaded >= max_download: break
        vid_id = v.get("id")
        # choose a video file (prefer 720/1080)
        files = v.get("video_files", [])
        if not files: continue
        file_choice = sorted(files, key=lambda x: x.get("height", 0), reverse=True)[0]
        video_url = file_choice.get("link")
        filename = OUT_DIR / f"pexels_{vid_id}_{file_choice.get('id')}.mp4"
        if filename.exists(): 
            print("Already downloaded:", filename)
            continue
        print("Downloading Pexels clip:", video_url)
        ok = download_url_to_file(video_url, filename)
        if not ok: continue
        # get metadata
        width = file_choice.get("width")
        height = file_choice.get("height")
        duration = v.get("duration")
        license_label = "Pexels"  # Pexels license: free for commercial use (verify current TOS)
        save_metadata_row(["pexels", vid_id, v.get("url"), str(filename), width, height, duration, license_label, topic, time.time()])
        downloaded += 1

    # # Pixabay
    # if downloaded < max_download:
    #     hits = search_pixabay_videos(topic, per_page=20)
    #     for h in hits:
    #         if downloaded >= max_download: break
    #         vid_id = h.get("id")
    #         # pick first video url
    #         vids = h.get("videos", {})
    #         # videos has keys like 'large', 'medium'...
    #         # choose 'large' or highest
    #         sizes = sorted(vids.items(), key=lambda x: int(x[1].get('height',0)), reverse=True)
    #         if not sizes: continue
    #         url = sizes[0][1].get("url")
    #         filename = OUT_DIR / f"pixabay_{vid_id}.mp4"
    #         if filename.exists():
    #             print("Already downloaded:", filename)
    #             continue
    #         print("Downloading Pixabay clip:", url)
    #         ok = download_url_to_file(url, filename)
    #         if not ok: continue
    #         width = sizes[0][1].get("width")
    #         height = sizes[0][1].get("height")
    #         duration = h.get("duration")
    #         license_label = "Pixabay"
    #         save_metadata_row(["pixabay", vid_id, h.get("pageURL"), str(filename), width, height, duration, license_label, topic, time.time()])
    #         downloaded += 1

    print(f"Downloaded {downloaded} clips for topic: {topic}")

# ---------- run ----------
if __name__ == "__main__":
    # topics = ["motivational", "technology", "meditation"]  # change as needed
      # change as needed
    if len(sys.argv) < 2:
        print("Usage: python main.py <topic>")
        sys.exit(1)

    topic = sys.argv[1]
    topics = [topic]
    print(f"Generating video for topic: {topic}")
    for t in topics:
        process_topic(t, max_download=3)
    print("Done.")
