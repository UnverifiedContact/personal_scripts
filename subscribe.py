# Minimal YouTube subscription helper using YouTube Data API v3.
import json
import os
import sys
import urllib.parse
import urllib.request


def string_in_file(value, file_path):
    with open(file_path, "r") as handle:
        return value in handle.read()


def is_subscribed(channel_hash, newsboat_urls_file):
    return string_in_file(channel_hash, newsboat_urls_file)


def sub(channel_hash, channel_name, file_path):
    rss_url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + channel_hash
    line = rss_url + ' "' + channel_name + '"'
    print(line)
    with open(file_path, "a") as handle:
        handle.write(line + "\n")


def parse_resource(url):
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    path = (parsed.path or "").rstrip("/")
    params = dict(urllib.parse.parse_qsl(parsed.query))

    if host.endswith("youtu.be"):
        return "video", path.lstrip("/")
    if path.startswith("/shorts/"):
        return "video", path.split("/shorts/")[1]
    if params.get("v"):
        return "video", params["v"]
    if path.startswith("/watch"):
        sys.exit("Missing video id in watch url.")
    if params.get("list") and not params.get("v"):
        return "playlist", params["list"]
    if path.startswith("/playlist"):
        sys.exit("Missing playlist id in playlist url.")
    if path.startswith("/channel/"):
        channel_id = path.split("/channel/")[1]
        return "channel_id", channel_id
    if path.startswith("/@"):
        return "channel_handle", path[2:]
    if path.startswith("/user/"):
        return "channel_username", path.split("/user/")[1]
    if path.startswith("/c/"):
        return "channel_custom", path.split("/c/")[1]
    sys.exit("Unsupported YouTube URL: " + url)


def fetch(endpoint, params, api_key):
    params = params.copy()
    params["key"] = api_key
    url = (
        "https://www.googleapis.com/youtube/v3/"
        + endpoint
        + "?"
        + urllib.parse.urlencode(params)
    )
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


if len(sys.argv) < 2:
    sys.exit("Didn't get a link argument.")

NEWSBOAT_FILE = os.getenv("NEWSBOAT_URLS_FILE")
if not NEWSBOAT_FILE:
    sys.exit("URL file env var is not set.")

API_KEY = os.getenv("YOUTUBE_V3_API_KEY")
if not API_KEY:
    sys.exit("YOUTUBE_V3_API_KEY is not set.")

resource_type, identifier = parse_resource(sys.argv[1])

if resource_type == "video":
    data = fetch("videos", {"part": "snippet", "id": identifier}, API_KEY)
elif resource_type == "playlist":
    data = fetch("playlists", {"part": "snippet", "id": identifier}, API_KEY)
elif resource_type == "channel_id":
    data = fetch("channels", {"part": "snippet", "id": identifier}, API_KEY)
elif resource_type == "channel_username":
    data = fetch(
        "channels",
        {"part": "snippet", "forUsername": identifier},
        API_KEY,
    )
elif resource_type == "channel_handle":
    data = fetch(
        "channels",
        {"part": "snippet", "forHandle": identifier},
        API_KEY,
    )
elif resource_type == "channel_custom":
    data = fetch(
        "search",
        {
            "part": "snippet",
            "q": identifier,
            "type": "channel",
            "maxResults": 1,
        },
        API_KEY,
    )
else:
    sys.exit("Unsupported resource type: " + resource_type)

items = data.get("items")
if not items:
    sys.exit("No data found for: " + identifier)

item = items[0]
if resource_type == "channel_custom":
    channel_id = item["id"]["channelId"]
    channel_name = item["snippet"]["title"]
else:
    snippet = item["snippet"]
    channel_id = snippet.get("channelId", item["id"])
    channel_name = snippet["channelTitle"] if "channelTitle" in snippet else snippet["title"]

# For playlists, respect uploader info (the playlist owner).
if resource_type == "playlist":
    channel_id = snippet["channelId"]
    channel_name = snippet["channelTitle"]

if is_subscribed(channel_id, NEWSBOAT_FILE):
    sys.exit("Already found in file: " + channel_id + " - " + channel_name)

sub(channel_id, channel_name, NEWSBOAT_FILE)

