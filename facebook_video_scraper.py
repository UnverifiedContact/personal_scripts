import requests
from bs4 import BeautifulSoup
import argparse
import sys
import re
import unicodedata

def clean_text(title):
    """
    Clean a string by removing special characters and normalizing spaces,
    but without truncation.
    """
    if not title:
        return "untitled"
    
    # First remove Unicode escape sequences
    title = re.sub(r'\\u[0-9a-fA-F]{4}', '', title)
    
    # Remove emojis and other non-printable characters
    title = ''.join(char for char in title if unicodedata.category(char)[0] != 'C')
    
    # Replace multiple spaces with single space
    title = re.sub(r'\s+', ' ', title)
    
    # Remove or replace invalid filename characters
    title = re.sub(r'[<>:"/\\|?*]', '', title)
    
    # Remove hashtags and their content
    title = re.sub(r'#\w+', '', title)
    
    # Remove URLs
    title = re.sub(r'http\S+', '', title)
    
    # Remove newlines and extra whitespace
    title = title.replace('\n', ' ').strip()
    
    # Remove any remaining special characters
    title = re.sub(r'[^\w\s-]', '', title)
    
    # Replace multiple spaces with single space again
    title = re.sub(r'\s+', ' ', title)
    
    return title.strip()

def clean_filename(title):
    """
    Clean a string to make it safe for use as a filename.
    Removes emojis, special characters, and normalizes spaces.
    """
    # Clean the text first
    title = clean_text(title)
    
    # Truncate if too long (max 100 chars)
    if len(title) > 100:
        title = title[:100]
    
    return title.strip()

def get_facebook_video_metadata(url):
    """
    Extract metadata from a Facebook video page.
    
    Args:
        url (str): URL of the Facebook video page
        
    Returns:
        dict: Dictionary containing metadata fields
    """
    try:
        # Send a GET request to the URL with browser-like headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Create a session to handle cookies
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract metadata from meta tags
        metadata = {}
        
        # Get raw title from twitter:description
        title_tag = soup.find('meta', {'name': 'twitter:description'})
        metadata['raw_title'] = title_tag['content'] if title_tag else None
        
        # Get uploader from the title meta tag (it's at the end after the | symbol)
        og_title = soup.find('meta', property='og:title')
        if og_title and '|' in og_title['content']:
            metadata['uploader'] = og_title['content'].split('|')[-1].strip()
        else:
            metadata['uploader'] = "Unknown"
        
        # Extract video ID from URL
        video_id = None
        if 'reel/' in url:
            video_id = url.split('reel/')[-1].split('?')[0]
        elif 'videos/' in url:
            video_id = url.split('videos/')[-1].split('?')[0]
        metadata['id'] = video_id
        
        # Clean the title for different uses
        metadata['clean_title'] = clean_text(metadata['raw_title'])
        metadata['short_title'] = clean_filename(metadata['raw_title'])
        
        # Create yt-dlp style filenames
        metadata['ytdlp_filename'] = f"{metadata['uploader']} - {metadata['short_title']} [{metadata['id']}]"
        metadata['ytdlp_filename_full'] = f"{metadata['uploader']} - {metadata['clean_title']} [{metadata['id']}]"
        
        # Add .mp4 extension versions
        metadata['ytdlp_filename_mp4'] = metadata['ytdlp_filename'] + '.mp4'
        metadata['ytdlp_filename_full_mp4'] = metadata['ytdlp_filename_full'] + '.mp4'
        
        return metadata
        
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error processing the page: {e}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description='Extract metadata from a Facebook video page')
    parser.add_argument('url', help='URL of the Facebook video page')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                      help='Output format (text or json)')
    
    args = parser.parse_args()
    
    result = get_facebook_video_metadata(args.url)
    if result:
        if args.format == 'json':
            import json
            print(json.dumps(result, indent=2))
        else:
            print("Video Metadata:")
            print(f"Raw Title: {result['raw_title']}")
            print(f"Clean Title: {result['clean_title']}")
            print(f"Short Title: {result['short_title']}")
            print(f"Uploader: {result['uploader']}")
            print(f"Video ID: {result['id']}")
            print("\nFilenames:")
            print(f"yt-dlp (short): {result['ytdlp_filename']}")
            print(f"yt-dlp (full): {result['ytdlp_filename_full']}")
            print(f"yt-dlp (short) with .mp4: {result['ytdlp_filename_mp4']}")
            print(f"yt-dlp (full) with .mp4: {result['ytdlp_filename_full_mp4']}")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main() 