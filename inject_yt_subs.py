#!/usr/bin/env python3
from pymediainfo import MediaInfo
import sys
import os.path
import re
from urllib.parse import urlparse, parse_qs
import requests
import json
import subprocess
import shutil

def main():
    if not sys.argv[1:]:
        print("Usage: inject_yt_subs.py <media_file>")
        sys.exit(2)

    media_file = sys.argv[1]
    if not os.path.exists(media_file):
        sys.exit("File not found.")

    media_info = MediaInfo.parse(media_file)
    general_tracks = [t for t in media_info.tracks if t.track_type == "General"]
    general_track = general_tracks[0] if general_tracks else None

    if not general_track:
        print(f"No general track found in {media_file}.")
        sys.exit(1)

    purl = getattr(general_track, "purl", None)
    
    video_id = extract_youtube_id(purl)
    if not video_id:
        sys.exit("Could not extract video ID from purl attribute.")

    
    resp = requests.get(f"http://127.0.0.1:5485/transcript/{video_id}")
    data = resp.json()
    transcript_items = data.get("transcript") or []
    vtt = transcript_to_vtt(transcript_items)

    tmp_dir = os.environ.get("TMP", "/tmp")
    base_name = os.path.splitext(os.path.basename(media_file))[0]
    vtt_path = os.path.join(tmp_dir, f"{base_name}.vtt")
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write(vtt)

    muxed_path = os.path.join(tmp_dir, f"{base_name}.muxed.mkv")

    # Mux WebVTT into the MKV as a subtitle stream
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", media_file,
        "-i", vtt_path,
        "-map", "0",
        "-map", "1",
        "-c", "copy",
        "-c:s", "webvtt",
        muxed_path,
    ]

    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit("ffmpeg failed to mux subtitles")

    # Overwrite original with rsync showing progress
    rsync_cmd = [
        "rsync", "-a", "--info=progress2", muxed_path, media_file
    ]
    rsync_result = subprocess.run(rsync_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if rsync_result.returncode != 0:
        print(rsync_result.stderr)
        sys.exit("rsync failed to overwrite the original file")


    result = dict(data)
    if "transcript" in result:
        result.pop("transcript", None)
    result["purl"] = purl
    #result["video_path"] = os.path.basename(media_file)
    result["video_file"] = os.path.basename(media_file)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def format_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    hours = total_ms // 3_600_000
    remainder = total_ms % 3_600_000
    minutes = remainder // 60_000
    remainder = remainder % 60_000
    secs = remainder // 1000
    millis = remainder % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def transcript_to_vtt(items: list[dict]) -> str:
    lines = ["WEBVTT", ""]
    for index, item in enumerate(items, start=1):
        start = float(item.get("start", 0))
        duration = float(item.get("duration", 0))
        end = start + duration
        text = str(item.get("text", ""))
        start_ts = format_timestamp(start)
        end_ts = format_timestamp(end)
        lines.append(f"{index}")
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def extract_youtube_id(value: str) -> str | None:
    if not value:
        return None
    value = value.strip()
    
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value
    
    parsed = urlparse(value)
    
    if parsed.hostname in ("www.youtube.com", "youtube.com"):
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        m = re.match(r"^/(embed|shorts)/([^/?#&]+)", parsed.path)
        if m:
            return m.group(2)
    
    if parsed.hostname == "youtu.be":
        return parsed.path.lstrip("/")
    
    return None

if __name__ == "__main__":
    main()