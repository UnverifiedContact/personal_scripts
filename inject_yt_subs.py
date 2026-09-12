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
import errno
import time


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


class ProcessError(Exception):
    """Raised by process_file() instead of exiting, so a batch run can move
    on to the next file. `code` follows exit_with()'s convention: 0 is a
    benign skip (nothing wrong, just nothing to do), non-zero is a real
    failure.
    """
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def safe_decode_bytes(data: bytes) -> str:
    """Safely decode bytes to string, handling encoding errors gracefully."""
    if data is None:
        return ""
    return data.decode('utf-8', errors='replace')


def replace_file(src: str, dst: str) -> None:
    """We used to shell out to rsync here, but it started refusing to touch
    our (symlinked) destination after a security fix in rsync 3.5.0. This
    replaces it: rename when possible, safe copy when not, so dst is
    never left half-written either way.
    """
    try:
        os.replace(src, dst)
        return
    except OSError as e:
        if e.errno != errno.EXDEV:
            raise
    staged = dst + ".part"
    shutil.copyfile(src, staged)
    os.replace(staged, dst)
    os.remove(src)

def extract_youtube_id(general_track):

    purl = getattr(general_track, "purl", None)
    comment = getattr(general_track, "comment", None)

    if purl:
        return determine_video_id(purl)
    if comment:
        return determine_video_id(comment)

    return None

def fetch_transcript_response(video_id: str) -> requests.Response:
    """GET the transcript, restarting the local transcript_service and retrying
    if it's not reachable. Termux kills the background gunicorn process, so a
    plain connection-refused here doesn't mean the transcript is unavailable --
    it means the service needs restarting first.
    """
    url = f"http://127.0.0.1:5485/transcript/{video_id}"
    try:
        return requests.get(url, timeout=30)
    except requests.exceptions.ConnectionError:
        pass

    start_script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "transcript_service", "start_gunicorn.sh"
    )
    subprocess.run(
        ["bash", start_script], check=False, timeout=15,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        try:
            return requests.get(url, timeout=30)
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)

    return requests.get(url, timeout=30)

def check_disk_space(media_file: str, tmp_dir: str) -> tuple[bool, str]:
    """Check free space on both the temp dir's filesystem (where ffmpeg
    writes the full muxed copy) and the destination dir's filesystem
    (where replace_file() has to stage a copy if it's a different
    filesystem than tmp_dir). -c copy remuxing doesn't re-encode, so the
    muxed output is roughly the same size as the input plus a negligible
    subtitle track; require a margin on top for safety.
    """
    needed = os.path.getsize(media_file)
    needed += max(int(needed * 0.1), 100 * 1024 * 1024)

    dest_dir = os.path.dirname(os.path.abspath(media_file)) or "."

    for label, path in (("temp dir", tmp_dir), ("destination dir", dest_dir)):
        free = shutil.disk_usage(path).free
        if free < needed:
            return False, (
                f"not enough disk space in {label} ({path}): "
                f"need ~{needed // (1024 * 1024)} MiB, have {free // (1024 * 1024)} MiB free"
            )
    return True, ""


def check_file(media_file: str, tmp_dir: str) -> tuple[bool, str]:
    """Run the cheap, local, non-mutating checks that decide whether a file
    is worth attempting. Returns (will_process, reason) -- reason is only
    meaningful when will_process is False.
    """
    if not os.path.exists(media_file):
        return False, "file not found"

    if has_subtitle_tracks(media_file):
        return False, "subtitle tracks already present"

    library_file = find_mediainfo_lib()
    try:
        media_info = MediaInfo.parse(media_file, library_file=library_file)
    except Exception as e:
        return False, f"could not read media info ({e})"

    general_tracks = [t for t in media_info.tracks if t.track_type == "General"]
    general_track = general_tracks[0] if general_tracks else None
    if not general_track:
        return False, "no general track found"

    if not extract_youtube_id(general_track):
        return False, "no YouTube video ID found in metadata"

    ok, reason = check_disk_space(media_file, tmp_dir)
    if not ok:
        return False, reason

    return True, ""


def process_file(media_file: str, tmp_dir: str) -> None:
    """Do the actual work for one file. Raises ProcessError instead of
    exiting, so a batch run can report a failure and continue with the
    next file.
    """
    if not os.path.exists(media_file):
        raise ProcessError(1, "File not found.")

    if has_subtitle_tracks(media_file):
        raise ProcessError(0, f"Subtitle tracks already present in {media_file}.")

    library_file = find_mediainfo_lib()
    media_info = MediaInfo.parse(media_file, library_file=library_file)
    general_tracks = [t for t in media_info.tracks if t.track_type == "General"]
    general_track = general_tracks[0] if general_tracks else None

    if not general_track:
        raise ProcessError(1, f"No general track found in \"{media_file}\".")

    video_id = extract_youtube_id(general_track)
    if not video_id:
        raise ProcessError(0, "Could not find video ID in metadata.. Maybe not a YouTube video?")

    ok, reason = check_disk_space(media_file, tmp_dir)
    if not ok:
        raise ProcessError(1, reason)

    try:
        resp = fetch_transcript_response(video_id)
        if not resp.ok:
            raise ProcessError(0, f"Transcript service unavailable (HTTP {resp.status_code}), skipping subtitle injection")

        data = resp.json()
        transcript_items = data.get("transcript") or []
        vtt = transcript_to_vtt(transcript_items)

        base_name = os.path.splitext(os.path.basename(media_file))[0]
        vtt_path = os.path.join(tmp_dir, f"{base_name}.vtt")
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write(vtt)

        try:
            # Embed subtitles using appropriate method for file format
            muxed_path = embed_subtitles_by_format(media_file, vtt_path, tmp_dir)

            # Overwrite original with the muxed file
            replace_file(muxed_path, media_file)
        finally:
            # Always clean up the .vtt, whether we succeeded or not
            try:
                os.remove(vtt_path)
            except OSError:
                pass

        size_mib = os.path.getsize(media_file) / (1024 * 1024)
        print(f"Subtitles embedded: {os.path.basename(media_file)} ({size_mib:.1f} MiB)", file=sys.stderr, flush=True)

        result = dict(data)
        if "transcript" in result:
            result.pop("transcript", None)
        result["video_file"] = os.path.basename(media_file)
        print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)

    except requests.exceptions.RequestException as e:
        raise ProcessError(0, f"Transcript service unavailable ({e}), skipping subtitle injection")


def confirm_batch(included: list[str], excluded: list[tuple[str, str]]) -> bool:
    """Print the preview report and ask the user to confirm. Returns True
    to proceed.
    """
    print(f"Checked {len(included) + len(excluded)} file(s):", file=sys.stderr)

    if included:
        print("\nWill process:", file=sys.stderr)
        for path in included:
            print(f"  {path}", file=sys.stderr)

    if excluded:
        print("\nWill skip:", file=sys.stderr)
        for path, reason in excluded:
            print(f"  {path} -- {reason}", file=sys.stderr)

    if not included:
        print("\nNothing to process.", file=sys.stderr)
        return False

    print(f"\n{len(included)} to process, {len(excluded)} to skip.", file=sys.stderr, flush=True)
    try:
        answer = input("Proceed? [Y/n] ").strip().lower()
    except EOFError:
        print("\nNo input available, aborting.", file=sys.stderr)
        return False
    return answer in ("", "y", "yes")


def main():
    paths = sys.argv[1:]
    if not paths:
        exit_with(2, "Usage: inject_yt_subs.py <media_file> [<media_file> ...]")

    tmp_dir = os.environ.get("TMP")
    if not tmp_dir:
        exit_with(1, "TMP environment variable not set")

    if len(paths) == 1:
        try:
            process_file(paths[0], tmp_dir)
        except ProcessError as e:
            exit_with(e.code, e.message)
        sys.exit(0)

    included = []
    excluded = []
    for path in paths:
        ok, reason = check_file(path, tmp_dir)
        if ok:
            included.append(path)
        else:
            excluded.append((path, reason))

    if not confirm_batch(included, excluded):
        exit_with(0, "Aborted.")

    failures = []
    for path in included:
        try:
            process_file(path, tmp_dir)
        except ProcessError as e:
            prefix = "INFO" if e.code == 0 else "ERROR"
            print(f"{prefix}: {path}: {e.message}", file=sys.stderr, flush=True)
            if e.code != 0:
                failures.append(path)

    print(f"\nDone: {len(included) - len(failures)} succeeded, {len(failures)} failed.", file=sys.stderr, flush=True)
    sys.exit(1 if failures else 0)


def format_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    hours = total_ms // 3_600_000
    remainder = total_ms % 3_600_000
    minutes = remainder // 60_000
    remainder = remainder % 60_000
    secs = remainder // 1000
    millis = remainder % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def embed_subtitles_mkv(media_file: str, vtt_path: str, muxed_path: str) -> None:
    """
    Embed WebVTT subtitles into an MKV file using ffmpeg.
    
    Args:
        media_file: Path to the original media file
        vtt_path: Path to the WebVTT subtitle file
        muxed_path: Path where the muxed file will be saved
    """
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
    
    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        # Forward ffmpeg stderr to our stderr to avoid stdout noise
        stderr_text = safe_decode_bytes(result.stderr)
        sys.stderr.write(stderr_text)
        # ffmpeg can leave a partial file behind (e.g. on ENOSPC); don't
        # let it sit in tmp and eat further disk space
        try:
            os.remove(muxed_path)
        except OSError:
            pass
        raise ProcessError(1, "ffmpeg failed to mux subtitles into MKV")


def embed_subtitles_mp4(media_file: str, vtt_path: str, muxed_path: str) -> None:
    """
    Embed WebVTT subtitles into an MP4 file using ffmpeg.
    
    Args:
        media_file: Path to the original media file
        vtt_path: Path to the WebVTT subtitle file
        muxed_path: Path where the muxed file will be saved
    """
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", media_file,
        "-i", vtt_path,
        "-map", "0",
        "-map", "1",
        "-c", "copy",
        "-c:s", "mov_text",  # MP4 uses mov_text codec for subtitles
        muxed_path,
    ]
    
    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        # Forward ffmpeg stderr to our stderr to avoid stdout noise
        stderr_text = safe_decode_bytes(result.stderr)
        sys.stderr.write(stderr_text)
        # ffmpeg can leave a partial file behind (e.g. on ENOSPC); don't
        # let it sit in tmp and eat further disk space
        try:
            os.remove(muxed_path)
        except OSError:
            pass
        raise ProcessError(1, "ffmpeg failed to mux subtitles into MP4")


def embed_subtitles_by_format(media_file: str, vtt_path: str, tmp_dir: str) -> str:
    """
    Embed subtitles into a media file using the appropriate method based on file format.
    
    Args:
        media_file: Path to the original media file
        vtt_path: Path to the WebVTT subtitle file
        tmp_dir: Directory for temporary files
        
    Returns:
        Path to the muxed file
    """
    base_name = os.path.splitext(os.path.basename(media_file))[0]
    file_ext = os.path.splitext(media_file)[1].lower()
    muxed_path = os.path.join(tmp_dir, f"{base_name}.muxed{file_ext}")

    # Choose appropriate embedding function based on file type
    if file_ext == ".mkv":
        embed_subtitles_mkv(media_file, vtt_path, muxed_path)
    elif file_ext == ".mp4":
        embed_subtitles_mp4(media_file, vtt_path, muxed_path)
    else:
        # Default to MKV for unknown formats
        embed_subtitles_mkv(media_file, vtt_path, muxed_path)
    
    return muxed_path


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
    proc = subprocess.run(ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        return False
    stdout_text = safe_decode_bytes(proc.stdout)
    payload = json.loads(stdout_text or "{}")
    streams = payload.get("streams") or []
    return len(streams) > 0

if __name__ == "__main__":
    main()