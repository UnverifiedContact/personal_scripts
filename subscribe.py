#import youtube_dl
import yt_dlp
import json
import sys
import os

def is_subscribed(channel_hash, NEWSBOAT_URLS_FILE):
    return string_in_file(channel_hash, NEWSBOAT_URLS_FILE);

def string_in_file(str, file_path):
    with open(file_path, 'r') as file:
        content = file.read()
        if str in content:
            return True;
    return False;

def sub(channel_hash, channel_name, file):
    rss_url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + channel_hash;
    #line = '"' + rss_url + '"' + ' ' + '"' + channel_name + '"';
    line = rss_url + ' ' + '"' + channel_name + '"'; 
    print(line);
    f = open(file, 'a');
    f.writelines([line + "\n"]);

NEWSBOAT_URLS_FILE = os.getenv('NEWSBOAT_URLS_FILE');
if NEWSBOAT_URLS_FILE is None:
    sys.exit("URL file env var is not set.");

if len(sys.argv) < 2:
    sys.exit("Didn't get a link argument.");

url = sys.argv[1]
ydl = yt_dlp.YoutubeDL({'outtmpl': '%(id)s.%(ext)s'})

with ydl:
    result = ydl.extract_info(
        url,
        download = False
    )

if 'entries' in result:
    # Can be a playlist or a list of videos
    video = result['entries'][0]
else:
    # Just a video
    video = result

#video = result if 'entries' not in result else video = result['entries'][0];
#print(json.dumps(video ,indent=4));

title = video['title'];
channel_hash = video['channel_id']; # the hash id for the channel
channel_name = video['uploader']; 

if is_subscribed(channel_hash, NEWSBOAT_URLS_FILE):
   sys.exit("Already found in file: " + channel_hash + ' - ' + channel_name);

sub(channel_hash, channel_name, NEWSBOAT_URLS_FILE);

