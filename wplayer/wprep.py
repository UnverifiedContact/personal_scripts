#!/usr/bin/env python3
"""
wprep.py - package video files for browser playback with player.html (Video.js).

For each input, creates a self-contained folder <out>/<name>/ (out: -o, $WPLAYER_OUT, or the current dir):
  index.html      player page; serve the folder and share its URL
  <name>.mp4      video copied (never re-encoded); audio copied, or AAC 96k stereo if browsers can't play it
  <name>.<lang>.vtt subtitles (embedded text subs + loose name*.srt/.vtt/.ass files next to the input)
Multiple audio tracks: the English one is used, or the file is skipped.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
from urllib.parse import quote

COPY_VIDEO = {"h264", "hevc", "av1", "vp9"}
COPY_AUDIO = {"aac", "mp3", "opus"}
TEXT_SUBS = {"subrip", "ass", "ssa", "webvtt", "mov_text", "text"}
LOOSE_SUBS = (".srt", ".vtt", ".ass", ".ssa")
MIN_CUES = 50  # fewer subtitle lines than this looks like junk
PLAYER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "player.html")


class Skip(Exception):
    """This file can't be prepared; the message says why."""


def probe(path: str) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", path],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise Skip(f"ffprobe failed: {out.stderr.strip()}")
    return json.loads(out.stdout)


def lang(stream: dict) -> str:
    code = stream.get("tags", {}).get("language", "")
    return "" if code in ("und", "unk") else code


def pick_audio(audios: list[dict]) -> dict | None:
    if len(audios) <= 1:
        return audios[0] if audios else None
    english = [a for a in audios if lang(a).lower() in ("en", "eng")]
    if not english:
        raise Skip(f"{len(audios)} audio tracks and none tagged English")
    return english[0]


def check_video(video: dict) -> None:
    codec = video["codec_name"]
    if codec not in COPY_VIDEO:
        raise Skip(f"{codec} video won't play in browsers (transcode it first)")
    if codec == "h264" and video.get("pix_fmt") not in ("yuv420p", "yuvj420p"):
        raise Skip(f"H.264 with {video.get('pix_fmt')} (10-bit/4:4:4) won't play in browsers")
    if codec == "hevc":
        print("  warning: HEVC plays in Chrome with a hardware decoder, mostly not in Firefox")


def sub_name(base: str, code: str, taken: set[str]) -> str:
    """name.en.vtt, or name.en.2.vtt if that's taken."""
    stem = f"{base}.{code or 'sub'}"
    name, n = f"{stem}.vtt", 1
    while name in taken:
        n += 1
        name = f"{stem}.{n}.vtt"
    taken.add(name)
    return name


def sub_looks_ok(vtt: str, source: str) -> bool:
    """Nearly-empty subtitle tracks are usually junk (e.g. a site ad): show them and ask whether to keep."""
    with open(vtt, encoding="utf-8", errors="replace") as f:
        blocks = f.read().split("\n\n")
    cues = []
    for block in blocks:
        lines = block.strip().splitlines()
        for i, line in enumerate(lines):
            if "-->" in line:
                cues.append(" / ".join(lines[i + 1:]))
                break
    if len(cues) >= MIN_CUES:
        return True
    print(f"  subs: warning: {source} has only {len(cues)} line(s):")
    for cue in cues[:5]:
        print(f"      {cue}")
    if not sys.stdin.isatty():
        print("  subs: not interactive, leaving it out")
        return False
    return input("  include it anyway? [y/N] ").strip().lower() in ("y", "yes")


def copy_with_progress(src: str, dst: str) -> None:
    """Copy src to dst, printing a percentage as it goes."""
    total, done, shown = os.path.getsize(src) or 1, 0, -1
    with open(src, "rb") as fin, open(dst, "wb") as fout:
        for chunk in iter(lambda: fin.read(8 << 20), b""):
            fout.write(chunk)
            done += len(chunk)
            pct = done * 100 // total
            if pct != shown:
                shown = pct
                print(f"\r  copying: {pct}% ({done >> 20}/{total >> 20} MB)", end="", flush=True)
    print()


def prepare(path: str, out_root: str, name: str | None, force: bool) -> None:
    print(f"== {path}")
    streams = probe(path)["streams"]
    videos = [s for s in streams if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")]
    audios = [s for s in streams if s["codec_type"] == "audio"]
    if not videos:
        raise Skip("no video stream")
    video, audio = videos[0], pick_audio(audios)
    check_video(video)

    base = name or os.path.splitext(os.path.basename(path))[0]
    final = os.path.join(out_root, base)
    if os.path.exists(final):
        if not force:
            raise Skip(f"{final} exists (use -f to overwrite)")
        if not os.path.isfile(os.path.join(final, "index.html")):
            raise Skip(f"{final} exists and isn't a wprep folder, not touching it")
    # Build in .partial, then swap it in by renames, so a failed run never leaves a half package.
    folder, old = final + ".partial", final + ".old"
    # Clear leftovers from earlier runs now, before any slow copying, and stop if that's impossible.
    for leftover in (folder, old):
        shutil.rmtree(leftover, ignore_errors=True)
        if os.path.exists(leftover):
            raise Skip(f"can't remove leftover {leftover} (a file in it is still open, e.g. by a player "
                       "or web server); close that and delete it, then re-run")
    os.makedirs(folder)
    try:
        package(path, folder, base, streams, video, audio, len(audios))
        # Renames work even while the old video is open (being played/served); deleting may not.
        if os.path.exists(final):
            os.rename(final, old)
        os.rename(folder, final)
    except BaseException:
        if not os.path.exists(final) and os.path.exists(old):
            os.rename(old, final)
        shutil.rmtree(folder, ignore_errors=True)
        raise
    shutil.rmtree(old, ignore_errors=True)
    if os.path.exists(old):
        print(f"  note: couldn't fully remove {old} (a file in it is still open); delete it later")
    print(f"  done: {final}/")


def package(path: str, folder: str, base: str, streams: list[dict], video: dict, audio: dict | None,
            n_audio: int) -> None:
    """Write the playable video, subtitles and index.html into folder."""
    audio_ok = audio is None or audio["codec_name"] in COPY_AUDIO
    ready = path.lower().endswith(".mp4") and audio_ok and n_audio <= 1
    media = base + ".mp4"

    cmd = ["ffmpeg", "-hide_banner", "-v", "warning", "-stats", "-y", "-i", path]
    if ready:
        print("  video: already browser-ready")
        copy_with_progress(path, os.path.join(folder, media))
    else:
        cmd += ["-map", f"0:{video['index']}", "-c:v", "copy"]
        if video["codec_name"] == "hevc":
            cmd += ["-tag:v", "hvc1"]
        if audio:
            cmd += ["-map", f"0:{audio['index']}"]
            cmd += ["-c:a", "copy"] if audio_ok else ["-c:a", "aac", "-b:a", "96k", "-ac", "2"]
        cmd += ["-movflags", "+faststart", os.path.join(folder, media)]
        print(f"  video: {video['codec_name']} copy")
        if audio:
            print(f"  audio: {audio['codec_name']} {'copy' if audio_ok else '-> aac 96k stereo'}")

    # Embedded subs ride along as extra outputs of the same ffmpeg run, so the file is read once.
    found, taken = [], set()  # found: (player entry, .vtt name, where it came from)
    for s in (s for s in streams if s["codec_type"] == "subtitle"):
        if s["codec_name"] not in TEXT_SUBS:
            print(f"  subs: skipping image-based {s['codec_name']} track")
            continue
        name = sub_name(base, lang(s), taken)
        cmd += ["-map", f"0:{s['index']}", "-c:s", "webvtt", os.path.join(folder, name)]
        found.append(({"src": quote(name), "lang": lang(s), "label": s.get("tags", {}).get("title", "")},
                      name, f"embedded track {s['index']}"))
        print(f"  subs: {s['codec_name']} -> {name}")

    if not ready or found:
        if subprocess.run(cmd).returncode != 0:
            raise Skip("ffmpeg failed")

    # Loose subtitle files next to the input: name.srt, name.en.srt, name.en.vtt, ...
    stem = os.path.splitext(os.path.abspath(path))[0]
    for loose in sorted(glob.glob(glob.escape(stem) + ".*")):
        filename = os.path.basename(loose)
        if not filename.lower().endswith(LOOSE_SUBS):
            continue
        code = loose[len(stem):].rsplit(".", 1)[0].strip(".")
        code = code if len(code) <= 3 else ""
        name = sub_name(base, code, taken)
        if subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-i", loose,
                           os.path.join(folder, name)]).returncode != 0:
            print(f"  subs: {filename} failed to convert, skipped")
            continue
        found.append(({"src": quote(name), "lang": code, "label": ""}, name, filename))
        print(f"  subs: {filename} -> {name}")

    subs = []
    for entry, name, source in found:
        if sub_looks_ok(os.path.join(folder, name), source):
            subs.append(entry)
        else:
            os.remove(os.path.join(folder, name))

    with open(PLAYER) as f:
        html = f.read()
    html = html.replace('const SRC = "";', f"const SRC = {json.dumps(quote(media))};", 1)
    html = html.replace("const SUBS = [];", "const SUBS = {};".format(json.dumps(subs).replace("</", "<\\/")), 1)
    with open(os.path.join(folder, "index.html"), "w") as f:
        f.write(html)


def main() -> None:
    parser = argparse.ArgumentParser(description="Make video files playable in the browser (MP4 + VTT + page).")
    parser.add_argument("inputs", nargs="+", help="video files")
    parser.add_argument("-o", "--out", default=os.environ.get("WPLAYER_OUT", "."),
                        help="where package folders go (default: $WPLAYER_OUT, else the current directory)")
    parser.add_argument("-n", "--name", help="package folder name (default: the input's filename); one input only")
    parser.add_argument("-f", "--force", action="store_true", help="overwrite an existing package")
    args = parser.parse_args()
    sys.stdout.reconfigure(line_buffering=True)
    if not os.path.isdir(args.out):
        sys.exit(f"wprep: output folder {args.out} doesn't exist")
    if args.name is not None and (len(args.inputs) > 1 or not args.name.strip() or "/" in args.name):
        sys.exit("wprep: --name needs exactly one input and a plain folder name")

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"wprep: {tool} not found")
    failed = 0
    for path in args.inputs:
        try:
            prepare(path, args.out, args.name, args.force)
        except Skip as e:
            print(f"  SKIPPED: {e}", file=sys.stderr)
            failed += 1
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
