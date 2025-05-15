#!/usr/bin/env python3

import os
import sys
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup
import subprocess
import re
from urllib.parse import unquote
import shutil
import base64
import argparse

def check_dependencies():
    try:
        import bs4
    except ImportError:
        print("beautifulsoup4 is required. Install it with: pip install beautifulsoup4")
        sys.exit(1)
    
    missing = []
    if shutil.which('aria2c') is None:
        missing.append("aria2c")
    if shutil.which('axel') is None:
        missing.append("axel")
    
    if missing:
        print(f"Missing required downloaders: {', '.join(missing)}")
        print("Install them with your package manager (e.g., apt install aria2c axel)")
        sys.exit(1)

def decode_url_filename(filename):
    """
    Properly decode URL-encoded filenames, handling special characters
    """
    # First decode URL encoding
    decoded = unquote(filename)
    # Handle any remaining URL encoding that might be double-encoded
    while '%' in decoded:
        try:
            new_decoded = unquote(decoded)
            if new_decoded == decoded:
                break
            decoded = new_decoded
        except:
            break
    return decoded

def sanitize_filename(filename):
    """
    Ensure filename is valid for the filesystem while preserving special characters
    """
    # Replace any forbidden characters with underscore
    forbidden = '<>:"/\\|?*'
    for char in forbidden:
        filename = filename.replace(char, '_')
    return filename.strip()

def normalize_url(url):
    """Normalize URL to ensure proper encoding while avoiding double-encoding"""
    parsed = urllib.parse.urlparse(url)
    # First decode to handle any existing encoding
    path = urllib.parse.unquote(parsed.path)
    # Then encode properly
    path = urllib.parse.quote(path)
    return urllib.parse.urlunparse((
        parsed.scheme,
        parsed.netloc,
        path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))

def parse_url(url):
    parsed = urllib.parse.urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path.rstrip('/')
    auth = None
    
    if '@' in parsed.netloc:
        auth = parsed.netloc.split('@')[0]
        base_url = f"{parsed.scheme}://{parsed.netloc.split('@')[1]}"
    
    return base_url, path, auth

def create_opener(auth):
    if auth:
        auth_handler = urllib.request.HTTPBasicAuthHandler()
        auth_handler.add_password(realm=None,
                                uri='/',
                                user=auth.split(':')[0],
                                passwd=auth.split(':')[1])
        opener = urllib.request.build_opener(auth_handler)
        urllib.request.install_opener(opener)

def get_html(url):
    try:
        print(f"Fetching URL: {url}")  # Debug print
        safe_url = normalize_url(url)
        print(f"Normalized URL: {safe_url}")  # Debug print
        with urllib.request.urlopen(safe_url) as response:
            return response.read()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        print(f"Tried safe URL: {safe_url}")
        sys.exit(1)

def parse_directory_listing(html):
    soup = BeautifulSoup(html, 'html.parser')
    entries = []
    
    for row in soup.find_all('tr'):
        link = row.find('a')
        if not link:
            continue
            
        name = link.get_text().strip()
        href = link.get('href')
        
        if name == "Parent Directory" or href == "../" or href.startswith("?"):
            continue
        
        # Properly decode both the visible name and the href
        decoded_name = decode_url_filename(name)
        decoded_href = decode_url_filename(href)
        
        # Sanitize the filename for filesystem
        safe_name = sanitize_filename(decoded_name)
            
        is_dir = row.find('img', alt='[DIR]') is not None
        entries.append((safe_name, decoded_href, is_dir))
    
    return entries

def download_file_aria2c(url, local_path, auth=None):
    print(f"\nDownloading with aria2c: {local_path}")
    print(f"URL: {url}")  # Debug print
    
    cmd = ['aria2c']
    cmd.extend([
        '--max-connection-per-server=16',
        '--continue=true',
        '--auto-file-renaming=false',
        '--check-integrity=true',
        '--retry-wait=3',
        '--max-tries=5',
        '--summary-interval=15',
        '--quiet=false',
        '--show-console-readout=true',
        '--allow-overwrite=true',
        '--remote-time=true'
    ])

    if auth:
        auth_b64 = base64.b64encode(auth.encode()).decode()
        cmd.extend(['--header', f'Authorization: Basic {auth_b64}'])
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    cmd.extend([
        '--dir', os.path.dirname(local_path),
        '--out', os.path.basename(local_path),
        url
    ])
    
    print(f"Command: {' '.join(cmd)}")  # Debug print
    
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error downloading {url}: {e}")
        return False

def download_file_axel(url, local_path, auth=None):
    print(f"\nDownloading with axel: {local_path}")
    print(f"URL: {url}")  # Debug print
    
    cmd = ['axel']
    if auth:
        url_parts = list(urllib.parse.urlparse(url))
        url_parts[1] = f"{auth}@{url_parts[1]}"
        url = urllib.parse.urlunparse(url_parts)
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    cmd.extend(['-a', url, '-o', local_path])
    
    print(f"Command: {' '.join(cmd)}")  # Debug print
    
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error downloading {url}: {e}")
        return False

def process_directory(base_url, current_path, local_base, auth=None, downloader='aria2c'):
    full_url = base_url + current_path
    print(f"\nProcessing directory: {full_url}")  # Debug print
    html = get_html(full_url)
    entries = parse_directory_listing(html)
    
    for name, href, is_dir in entries:
        print(f"\nProcessing entry: {name}")  # Debug print
        print(f"Original href: {href}")  # Debug print
        
        remote_path = urllib.parse.urljoin(current_path + '/', href)
        print(f"Remote path: {remote_path}")  # Debug print
        
        local_path = os.path.join(local_base, name)
        print(f"Local path: {local_path}")  # Debug print
        
        if is_dir:
            print(f"Creating directory: {local_path}")  # Debug print
            os.makedirs(local_path, exist_ok=True)
            process_directory(base_url, remote_path, local_base, auth, downloader)
        else:
            # If the file exists, attempt to download it
            if os.path.exists(local_path):
                print(f"File already exists: {local_path}, attempting to resume download.")
            
            # Proceed with the download, allowing the downloader to handle resuming
            download_url = normalize_url(base_url + remote_path)
            print(f"Download URL: {download_url}")  # Debug print
            if downloader == 'aria2c':
                download_file_aria2c(download_url, local_path, auth)
            else:
                download_file_axel(download_url, local_path, auth)

def main():
    parser = argparse.ArgumentParser(description='Download files from Apache directory listing')
    parser.add_argument('url', help='URL to download from')
    parser.add_argument('--downloader', choices=['aria2c', 'axel'], default='aria2c',
                      help='Choose download utility (default: aria2c)')
    
    args = parser.parse_args()
    
    check_dependencies()
    
    url = args.url.rstrip('/')
    base_url, path, auth = parse_url(url)
    
    if auth:
        create_opener(auth)
    
    local_base = os.path.basename(path)
    if not local_base:
        local_base = "download"
    
    local_base = sanitize_filename(decode_url_filename(local_base))
    os.makedirs(local_base, exist_ok=True)
    
    print(f"Starting download from {url}")
    print(f"Using downloader: {args.downloader}")
    print(f"Files will be saved in: {os.path.abspath(local_base)}")
    
    process_directory(base_url, path, local_base, auth, args.downloader)
    print("\nDownload completed!")

if __name__ == "__main__":
    main()
