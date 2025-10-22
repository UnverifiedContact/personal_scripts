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


def is_termux() -> bool:
    """Check if we're running on Termux."""
    return os.path.exists("/data/data/com.termux/files/usr")


def find_mediainfo_lib() -> str | None:
    """Find libmediainfo library for pymediainfo to use."""
    # If not Termux, let pymediainfo use its default behavior
    if not is_termux():
        return None
    
    # Only apply Termux-specific fix if we're actually on Termux
    termux_candidates = [
        "/data/data/com.termux/files/usr/lib/libmediainfo.so",
        "/data/data/com.termux/files/usr/lib/libmediainfo.so.0",
    ]
    for path in termux_candidates:
        if os.path.exists(path):
            return path
    
    # If no library found, let pymediainfo use its default behavior
    return None


def exit_with(code: int, message: str) -> None:
    """Write message (prefixed) to stderr and exit with the provided code."""
    prefix = "INFO" if code == 0 else ("USAGE" if code == 2 else "ERROR")
    if message:
        sys.stderr.write(f"{prefix}: {message}\n")
    sys.exit(code)

def extract_youtube_id(general_track):

    purl = getattr(general_track, "purl", None)
    comment = getattr(general_track, "comment", None)

    if purl:
        return determine_video_id(purl)
    if comment:
        return determine_video_id(comment)

    return None

def main():
    if not sys.argv[1:]:
        exit_with(2, "Usage: inject_yt_subs.py <media_file>")

    media_file = sys.argv[1]
    if not os.path.exists(media_file):
        exit_with(1, "File not found.")

    if has_subtitle_tracks(media_file):
        exit_with(0, f"Subtitle tracks already present in {media_file}.")

    library_file = find_mediainfo_lib()
    media_info = MediaInfo.parse(media_file, library_file=library_file)
    general_tracks = [t for t in media_info.tracks if t.track_type == "General"]
    general_track = general_tracks[0] if general_tracks else None

    if not general_track:
        exit_with(1, f"No general track found in \"{media_file}\".")

    video_id = extract_youtube_id(general_track)
    if not video_id:
        exit_with(0, "Could not find video ID in metadata.. Maybe not a YouTube video?")

    try:
        resp = requests.get(f"http://127.0.0.1:5485/transcript/{video_id}", timeout=30)
        if not resp.ok:
            exit_with(0, f"Transcript service unavailable (HTTP {resp.status_code}), skipping subtitle injection")
        
        data = resp.json()
        transcript_items = data.get("transcript") or []
        vtt = transcript_to_vtt(transcript_items)

        tmp_dir = os.environ.get("TMP")
        if not tmp_dir:
            exit_with(1, "TMP environment variable not set")
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
            # Forward ffmpeg stderr to our stderr to avoid stdout noise
            sys.stderr.write(result.stderr)
            exit_with(1, "ffmpeg failed to mux subtitles")

        # Overwrite original with rsync showing progress
        rsync_cmd = [
            "rsync", "-a", "--info=progress2", muxed_path, media_file
        ]
        rsync_result = subprocess.run(rsync_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if rsync_result.returncode != 0:
            sys.stderr.write(rsync_result.stderr)
            exit_with(1, "rsync failed to overwrite the original file")

        # Clean up temporary files
        try:
            os.remove(vtt_path)
            os.remove(muxed_path)
        except OSError:
            pass  # Ignore errors if files don't exist or can't be removed

        result = dict(data)
        if "transcript" in result:
            result.pop("transcript", None)
        result["video_file"] = os.path.basename(media_file)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0)
        
    except requests.exceptions.RequestException as e:
        exit_with(0, f"Transcript service unavailable ({e}), skipping subtitle injection")


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


def determine_video_id(value: str) -> str | None:
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

def has_subtitle_tracks(media_file: str) -> bool:
    """
    Use ffprobe to detect whether the media file already contains any subtitle streams.

    Returns True if at least one subtitle stream is present; False otherwise.
    """
    ffprobe_cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "s",
        "-show_entries", "stream=index",
        "-of", "json",
        media_file,
    ]
    proc = subprocess.run(ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        return False
    payload = json.loads(proc.stdout or "{}")
    streams = payload.get("streams") or []
    return len(streams) > 0

if __name__ == "__main__":
    main()