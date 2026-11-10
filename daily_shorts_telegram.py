
#!/usr/bin/env python3
"""
100% Free Daily Animated YouTube Shorts Generator -> Direct Telegram Delivery
"""

import asyncio
import datetime
import json
import os
import random
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

import edge_tts

OUTPUT_DIR = Path("build_output")
SCENES_DIR = OUTPUT_DIR / "scenes"
VOICE_NAME = os.getenv("EDGE_TTS_VOICE", "en-US-ChristopherNeural")
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

VIRAL_NICHES = [
    "Dark Psychology Tricks People Use Every Day Without Realizing",
    "Bizarre Historical Laws That Actually Existed in Ancient Civilizations",
    "Mind-Blowing Paradoxes of Time and Space Explained in 45 Seconds",
    "Stoic Mental Models for Instant Calm Under Extreme Pressure",
    "Everyday Inventions That Were Discovered Completely By Accident",
    "Strange Survival Rules That Sound Fake But Can Save Your Life",
]

def get_curated_storyboard(topic: str) -> dict:
    return {
        "title": f"{topic[:60]} #shorts",
        "caption_summary": f"Unbelievable facts about {topic.lower()}! #shorts #facts #viral #psychology",
        "scenes": [
            {
                "narration": f"Did you know that {topic.lower()} is happening all around you right now?",
                "image_prompt": f"2D stylized animated cartoon illustration, bold ink outlines, vibrant colors, dramatic scene about {topic}, vertical 9:16 composition, no text, no watermark",
            },
            {
                "narration": "Most people go their entire lives completely blind to how this actually works.",
                "image_prompt": "2D stylized animated cartoon illustration, expressive character looking shocked and confused, bold ink outlines, vertical 9:16 composition, no text, no watermark",
            },
            {
                "narration": "Psychologists discovered that your brain makes these critical decisions seconds before you even realize it.",
                "image_prompt": "2D stylized animated cartoon illustration, glowing human brain with colorful glowing neural pathways, vertical 9:16 composition, no text, no watermark",
            },
            {
                "narration": "Once you learn this simple pattern, you will start noticing it in almost every single conversation.",
                "image_prompt": "2D stylized animated cartoon illustration, two animated characters in an intense dramatic conversation, vertical 9:16 composition, no text, no watermark",
            },
            {
                "narration": "The smartest people use this exact mental trick to stay completely calm under extreme pressure.",
                "image_prompt": "2D stylized animated cartoon illustration, calm confident superhero character standing tall in a stormy city, vertical 9:16 composition, no text, no watermark",
            },
            {
                "narration": "And that is the exact reason why everyone needs to understand this before it happens again.",
                "image_prompt": "2D stylized animated cartoon illustration, mysterious glowing hourglass with swirling cosmic light, vertical 9:16 composition, no text, no watermark",
            },
        ],
    }

def create_fallback_card(dest_path: Path, scene_num: int) -> None:
    colors = ["#1a102f", "#0f2027", "#200122", "#16222f", "#191919", "#0d1b2a"]
    bg_color = colors[(scene_num - 1) % len(colors)]
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg_color}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:d=1",
        "-frames:v", "1",
        str(dest_path),
    ]
    subprocess.run(cmd, check=True)

def download_scene_image(prompt: str, dest_path: Path, seed: int, scene_num: int) -> None:
    encoded_prompt = urllib.parse.quote(prompt)
    image_url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width={VIDEO_WIDTH}&height={VIDEO_HEIGHT}&seed={seed}&nologo=true"
    )
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                image_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                dest_path.write_bytes(resp.read())
                print(f"Downloaded image for scene {scene_num}")
                return
        except Exception as e:
            print(f"Image API attempt {attempt+1} notice: {e}")
            time.sleep(1)

    print(f"Generated clean motion background for scene {scene_num}")
    create_fallback_card(dest_path, scene_num)

async def synthesize_scene_audio(text: str, audio_path: Path) -> float:
    communicate = edge_tts.Communicate(text, VOICE_NAME, rate="+8%")
    await communicate.save(str(audio_path))
    return get_audio_duration(audio_path)

def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return max(float(result.stdout.strip()), 1.5)

def render_animated_scene(image_path: Path, audio_path: Path, duration: float, output_clip_path: Path, zoom_in: bool = True) -> None:
    total_frames = int(duration * FPS) + 15
    zoom_expr = "min(zoom+0.0015,1.22)" if zoom_in else "if(eq(on,1),1.22,max(1.0,zoom-0.0015))"

    vf_filter = (
        f"scale=2160:3840,"
        f"zoompan=z='{zoom_expr}':d={total_frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={FPS},"
        f"format=yuv420p"
    )
    cmd = [
        "ffmpeg", "-y", "-loop", "1",
        "-i", str(image_path),
        "-i", str(audio_path),
        "-vf", vf_filter,
        "-t", f"{duration:.2f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(output_clip_path),
    ]
    subprocess.run(cmd, check=True)

def merge_scenes(scene_clips: list[Path], final_video_path: Path) -> None:
    concat_list = OUTPUT_DIR / "concat_list.txt"
    concat_list.write_text("\n".join(f"file '{clip.resolve()}'" for clip in scene_clips), encoding="utf-8")
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c:v", "libx264", "-preset", "fast", "-crf", "19",
            "-c:a", "aac", "-b:a", "192k",
            str(final_video_path)
        ],
        check=True,
    )

def send_to_telegram(video_path: Path, title: str, summary: str) -> None:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not (bot_token and chat_id):
        print("Telegram delivery skipped: credentials not provided.")
        return

    caption = f"🎬 {title}\n\n{summary}\n\n👉 Tap Save to Gallery -> Share to YouTube Shorts!"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"

    video_bytes = video_path.read_bytes()
    body = bytearray()

    def add_field(name: str, val: str):
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{val}\r\n".encode("utf-8"))

    add_field("chat_id", chat_id)
    add_field("caption", caption[:1024])
    add_field("supports_streaming", "true")

    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"video\"; filename=\"short.mp4\"\r\nContent-Type: video/mp4\r\n\r\n".encode("utf-8"))
    body.extend(video_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        if result.get("ok"):
            print("Successfully sent daily Short to Telegram!")
        else:
            print("Telegram error:", result)

async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SCENES_DIR.mkdir(parents=True, exist_ok=True)

    day_seed = int(datetime.date.today().strftime("%Y%m%d"))
    random.seed(day_seed)
    topic = os.getenv("CUSTOM_TOPIC") or random.choice(VIRAL_NICHES)
    print(f"[1/3] Generating storyboard: {topic}")
    storyboard = get_curated_storyboard(topic)

    scene_clips = []
    for idx, scene in enumerate(storyboard["scenes"], start=1):
        print(f"[2/3] Rendering Scene {idx}/6...")
        img_path = SCENES_DIR / f"scene_{idx:02d}.jpg"
        aud_path = SCENES_DIR / f"scene_{idx:02d}.mp3"
        clip_path = SCENES_DIR / f"scene_{idx:02d}.mp4"

        download_scene_image(scene["image_prompt"], img_path, seed=day_seed + idx, scene_num=idx)
        duration = await synthesize_scene_audio(scene["narration"], aud_path)

        render_animated_scene(
            image_path=img_path,
            audio_path=aud_path,
            duration=duration,
            output_clip_path=clip_path,
            zoom_in=(idx % 2 == 1),
        )
        scene_clips.append(clip_path)

    final_video = OUTPUT_DIR / "daily_viral_short.mp4"
    print("[3/3] Merging scenes and exporting final 1080x1920 Short...")
    merge_scenes(scene_clips, final_video)

    title = storyboard.get("title", "Daily Viral Short #shorts")
    caption = storyboard.get("caption_summary", "#shorts #facts #viral")
    print("Sending completed video to your Telegram...")
    send_to_telegram(final_video, title, caption)

if __name__ == "__main__":
    asyncio.run(main())
