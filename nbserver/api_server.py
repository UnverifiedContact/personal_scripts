import sqlite3
from urllib.parse import parse_qs, urlparse
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime
import os
import argparse
import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import concurrent.futures

# Parse command line arguments
parser = argparse.ArgumentParser(description='Newsboat API Server')
parser.add_argument('--db', default='newsboat_cache.db', help='Path to the newsboat cache database')
args = parser.parse_args()

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Path to your SQLite database
DB_PATH = args.db

# Thread-local storage for database connections
thread_local = threading.local()

def get_db():
    """Get a database connection for the current thread."""
    if not hasattr(thread_local, 'connection'):
        if not os.path.exists(DB_PATH):
            print(f"Error: Database file not found at {DB_PATH}")
            exit(1)
        try:
            thread_local.connection = sqlite3.connect(DB_PATH)
            thread_local.connection.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            print(f"Error: Failed to connect to database: {str(e)}")
            exit(1)
    return thread_local.connection

def column_exists(conn, table_name, column_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    return column_name in columns

def initialize_schema():
    conn = get_db()
    cursor = conn.cursor()

    if not column_exists(conn, 'rss_item', 'is_clickbait'):
        cursor.execute("ALTER TABLE rss_item ADD COLUMN is_clickbait BOOLEAN DEFAULT NULL")
        print("Added column: rss_item.is_clickbait")

    if not column_exists(conn, 'rss_item', 'fixed_title'):
        cursor.execute("ALTER TABLE rss_item ADD COLUMN rebait_title TEXT DEFAULT NULL")
        print("Added column: rss_item.fixed_title")
    
    conn.commit()

# Test database connection immediately
get_db()
initialize_schema()

@app.route('/')
def index():
    """Serve the frontend application."""
    return render_template('index.html')

def get_non_deleted_items(only_pending_clickbait=False):
    try:
        conn = get_db()
        cursor = conn.cursor()

        where_clause = "WHERE deleted = 0"
        if only_pending_clickbait:
            where_clause += " AND is_clickbait IS NULL"

        cursor.execute(f"""
            SELECT
                rss_item.id,
                rss_feed.title AS channel_name,
                rss_feed.url AS channel_url,
                rss_item.title,
                rss_item.url,
                rss_item.deleted,
                rss_item.unread,
                rss_item.pubDate,
                rss_item.content,
                rss_item.author,
                rss_item.feedurl,
                rss_item.flags,
                rss_item.is_clickbait
            FROM
                rss_item
            INNER JOIN
                rss_feed ON rss_item.feedurl = rss_feed.rssurl
            {where_clause}
            ORDER BY UPPER(channel_name) ASC;
        """)
        rows = cursor.fetchall()

        items = []
        for row in rows:
            pub_date = datetime.fromtimestamp(row['pubDate']).strftime('%Y-%m-%d %H:%M:%S')
            
            items.append({
                'id': row['id'],
                'channel_name': row['channel_name'],
                'channel_url': row['channel_url'],
                'title': row['title'],
                'url': row['url'],
                'deleted': row['deleted'],
                'unread': row['unread'],
                'pubDate': pub_date,
                'content': row['content'],
                'feedurl': row['feedurl'],
                'flags': row['flags'],
                'is_clickbait': row['is_clickbait']
            })
        
        return items
    except Exception as e:
        print(f"Error in get_non_deleted_items: {str(e)}")
        return []

@app.route('/api/items', methods=['GET', 'OPTIONS'])
def get_items():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        items = get_non_deleted_items()
        items = process_items(items)
        return jsonify({
            'status': 'success',
            'data': items
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/items/unqualified', methods=['GET', 'OPTIONS'])
def get_pending_clickbait_items():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        items = get_non_deleted_items(only_pending_clickbait=True)
        items = process_items(items)
        return jsonify({
            'status': 'success',
            'data': items
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def get_item_by_id(item_id):
    """Fetch a single item by ID from the database."""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                id,
                author,
                title,
                url,
                deleted,
                unread,
                pubDate,
                content,
                feedurl,
                flags
            FROM 
                rss_item
            WHERE 
                id = ? AND deleted = 0
        """, (item_id,))
        
        row = cursor.fetchone()

        if row is None:
            return None

        # Convert Unix timestamp to human readable date
        pub_date = datetime.fromtimestamp(row['pubDate']).strftime('%Y-%m-%d %H:%M:%S')
        
        return {
            'id': row['id'],
            'author': row['author'],
            'title': row['title'],
            'url': row['url'],
            'deleted': row['deleted'],
            'unread': row['unread'],
            'pubDate': pub_date,
            'content': row['content'],
            'feedurl': row['feedurl'],
            'flags': row['flags']
        }
    except Exception as e:
        print(f"Error in get_item_by_id: {str(e)}")
        return None

def get_item_flags(item_id):
    """Get the flags string for an item. Always returns a string, empty string if NULL or not found."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT flags FROM rss_item WHERE id = ? AND deleted = 0", (item_id,))
    row = cursor.fetchone()
    if not row or row['flags'] is None:
        return ''
    return row['flags']

def is_item_starred(item_id):
    """Check if an item is starred (has 'S' flag)."""
    flags = get_item_flags(item_id)
    return 'S' in flags or 's' in flags

def update_item_flags(item_id, flags_str):
    """Update the flags for an item. Normalizes the flags before writing. Returns True if rows were updated."""
    normalized = normalize_flags(flags_str)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE rss_item SET flags = ? WHERE id = ? AND deleted = 0", (normalized, item_id))
    conn.commit()
    return cursor.rowcount > 0

def mark_item_as_deleted(item_id):
    """Mark an item as deleted in the database."""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE rss_item 
            SET deleted = 1 
            WHERE id = ?
        """, (item_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        
        return success
    except Exception as e:
        print(f"Error in mark_item_as_deleted: {str(e)}")
        return False

def toggle_item_unread(item_id):
    """Toggle the unread flag for an item in the database. If setting to unread=1 (unkept), also remove star."""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Get current unread value
        cursor.execute("SELECT unread FROM rss_item WHERE id = ? AND deleted = 0", (item_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        current_unread = row['unread']
        new_unread = 1 if current_unread == 0 else 0

        # Toggle unread: unread = 1 -> 0, unread = 0 -> 1
        cursor.execute("""
            UPDATE rss_item
            SET unread = ?
            WHERE id = ? AND deleted = 0
        """, (new_unread, item_id))
        
        success = cursor.rowcount > 0
        
        # If setting to unread=1 (unkept), remove the star
        if success and new_unread == 1:
            set_item_starred(item_id, False)
        
        conn.commit()
        
        if not success:
            return None

        return new_unread
    except Exception as e:
        print(f"Error in toggle_item_unread: {str(e)}")
        return None

def handle_get_item(item_id):
    """Handle GET request for a single item."""
    item = get_item_by_id(item_id)
    if item is None:
        return jsonify({
            'status': 'error',
            'message': 'Item not found'
        }), 404

    return jsonify({
        'status': 'success',
        'data': item
    })

def handle_delete_item(item_id):
    """Handle DELETE request for a single item."""
    if mark_item_as_deleted(item_id):
        return jsonify({
            'status': 'success',
            'message': 'Item deleted successfully'
        })
    return jsonify({
        'status': 'error',
        'message': 'Item not found or already deleted'
    }), 404

def handle_toggle_unread(item_id):
    """Handle POST request to toggle unread status for a single item."""
    new_unread = toggle_item_unread(item_id)
    if new_unread is not None:
        # Get updated flags in case star was removed
        updated_flags = get_item_flags(item_id)
        is_starred = 'S' in updated_flags or 's' in updated_flags
        return jsonify({
            'status': 'success',
            'message': 'Unread status updated successfully',
            'data': {
                'unread': new_unread,
                'flags': updated_flags,
                'starred': is_starred
            }
        })
    return jsonify({
        'status': 'error',
        'message': 'Item not found or failed to update'
    }), 404

def remove_item_star_flag_only(item_id):
    """Remove the 'S' flag from an item's flags (without changing unread status)."""
    current_flags = get_item_flags(item_id)
    new_flags = remove_flag(current_flags, 'S')
    return update_item_flags(item_id, new_flags)

def set_item_star(item_id):
    """Add the 'S' flag to an item's flags and set unread=0 (kept)."""
    current_flags = get_item_flags(item_id)
    new_flags = add_flag(current_flags, 'S')
    flags_success = update_item_flags(item_id, new_flags)
    
    # Also set unread=0 (kept) when starring
    if flags_success:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE rss_item SET unread = 0 WHERE id = ? AND deleted = 0", (item_id,))
        conn.commit()
    
    return flags_success

def set_item_starred(item_id, starred):
    """Set or unset the starred status for an item. Returns True if successful."""
    if starred:
        return set_item_star(item_id)
    else:
        return remove_item_star_flag_only(item_id)

def remove_item_star(item_id):
    """Remove the 'S' flag from an item's flags and set unread=1 (not kept)."""
    flags_success = remove_item_star_flag_only(item_id)
    
    # Also set unread=1 (not kept) when unstarring
    if flags_success:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE rss_item SET unread = 1 WHERE id = ? AND deleted = 0", (item_id,))
        conn.commit()
    
    return flags_success

@app.route('/api/items/<int:item_id>', methods=['GET', 'DELETE', 'POST', 'OPTIONS'])
def handle_item(item_id):
    """Route handler that delegates to the appropriate method handler."""
    if request.method == 'OPTIONS':
        return '', 200

    method_handlers = {
        'GET': handle_get_item,
        'DELETE': handle_delete_item,
        'POST': handle_toggle_unread
    }
    
    handler = method_handlers.get(request.method)
    if handler:
        return handler(item_id)
    return jsonify({
        'status': 'error',
        'message': 'Method not allowed'
    }), 405

@app.route('/api/items/<int:item_id>/starred', methods=['POST', 'DELETE', 'OPTIONS'])
def handle_item_starred(item_id):
    """Handle setting or removing the starred flag for an item."""
    if request.method == 'OPTIONS':
        return '', 200
    
    # Verify item exists
    item = get_item_by_id(item_id)
    if item is None:
        return jsonify({
            'status': 'error',
            'message': 'Item not found'
        }), 404
    
    if request.method == 'POST':
        # Set starred flag
        success = set_item_star(item_id)
        if success:
            updated_flags = get_item_flags(item_id)
            # Get updated unread status
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT unread FROM rss_item WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            unread_status = row['unread'] if row else None
            return jsonify({
                'status': 'success',
                'message': 'Starred flag set successfully',
                'data': {
                    'flags': updated_flags,
                    'starred': True,
                    'unread': unread_status
                }
            }), 200
        return jsonify({
            'status': 'error',
            'message': 'Failed to set starred flag'
        }), 500
    
    elif request.method == 'DELETE':
        # Remove starred flag
        success = remove_item_star(item_id)
        if success:
            updated_flags = get_item_flags(item_id)
            # Get current unread status (unchanged when unstarring)
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT unread FROM rss_item WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            unread_status = row['unread'] if row else None
            return jsonify({
                'status': 'success',
                'message': 'Starred flag removed successfully',
                'data': {
                    'flags': updated_flags,
                    'starred': False,
                    'unread': unread_status
                }
            }), 200
        return jsonify({
            'status': 'error',
            'message': 'Failed to remove starred flag'
        }), 500
    
    return jsonify({
        'status': 'error',
        'message': 'Method not allowed'
    }), 405

def mark_items_as_deleted(item_ids):
    """Mark multiple items as deleted in the database."""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Create a parameterized query with the correct number of placeholders
        placeholders = ','.join('?' * len(item_ids))
        cursor.execute(f"""
            UPDATE rss_item 
            SET deleted = 1 
            WHERE id IN ({placeholders})
        """, item_ids)
        
        success = cursor.rowcount > 0
        conn.commit()
        
        return success
    except Exception as e:
        print(f"Error in mark_items_as_deleted: {str(e)}")
        return False

@app.route('/api/items/batch-delete', methods=['POST', 'OPTIONS'])
def handle_batch_delete():
    """Handle batch deletion of multiple items."""
    if request.method == 'OPTIONS':
        return '', 200

    if not request.is_json:
        return jsonify({
            'status': 'error',
            'message': 'Request must be JSON'
        }), 400

    data = request.get_json()
    if not isinstance(data, dict) or 'item_ids' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Request must include item_ids array'
        }), 400

    item_ids = data['item_ids']
    if not isinstance(item_ids, list):
        return jsonify({
            'status': 'error',
            'message': 'item_ids must be an array'
        }), 400

    if not all(isinstance(id, int) for id in item_ids):
        return jsonify({
            'status': 'error',
            'message': 'All item IDs must be integers'
        }), 400

    if mark_items_as_deleted(item_ids):
        return jsonify({
            'status': 'success',
            'message': f'Successfully deleted {len(item_ids)} items'
        })
    return jsonify({
        'status': 'error',
        'message': 'Failed to delete items'
    }), 500


def process_items(items):
    #items = process_dearrow(items)
    items = process_add_origin(items)
    items = process_add_youtube_id(items)
    return items

def process_add_origin(items):
    for item in items:
        item['origin'] = determine_origin(item['url'])
    return items

def process_add_youtube_id(items):
    for item in items:
        if youtube_id := extract_youtube_video_id(item['url']):
            item['youtube_id'] = youtube_id
    return items

def determine_origin(url):
    if '/shorts/' in url: return "youtube shorts"
    
    parsed = urlparse(url)
    return parsed.hostname or ""

def normalize_flags(flags_str):
    """Normalize flags: filter to A-Z/a-z, remove duplicates, sort alphabetically. Returns None if not a string or empty."""
    if not isinstance(flags_str, str):
        return None
    if not flags_str:
        return None
    chars = [c for c in flags_str if c.isalpha() and ((c >= 'A' and c <= 'Z') or (c >= 'a' and c <= 'z'))]
    if not chars:
        return None
    unique = list(dict.fromkeys(chars))
    result = ''.join(sorted(unique))
    return result if result else None

def add_flag(flags_str, char):
    flags_str = flags_str or ''
    return flags_str if char in flags_str else flags_str + char

def remove_flag(flags_str, char):
    return (flags_str or '').replace(char, '')
    
# business logic
def process_dearrow(items):
    """Process items through business logic."""
    # Get HTTP session once for all items
    session = initialize_http_session()
    
    for item in items:
        url = item['url']
        print(url)
        youtube_video_id = extract_youtube_video_id(url)
        print(youtube_video_id)
        if youtube_video_id is None: continue
        
        dearrow_info = http_get_dearrow_video_info(youtube_video_id, session)
        if dearrow_info is None: continue
        item['dearrow_info'] = dearrow_info
        item['original_title'] = item['title']

        try:
            item['title'] = dearrow_info['titles'][0]['title']
        except (KeyError, IndexError, TypeError):
            continue

        print(item)
        
    print('Finished processing items...')
    return items

def extract_youtube_video_id(url):
    parsed = urlparse(url)
    
    if parsed.hostname in ['www.youtube.com', 'youtube.com', 'm.youtube.com']:
        # Try to get ID from ?v=VIDEO_ID
        qs = parse_qs(parsed.query)
        if 'v' in qs:
            return qs['v'][0]
        # Otherwise, get last part of path if it's embed or v
        parts = parsed.path.split('/')
        if parts[-2] in ['embed', 'v']:
            return parts[-1]
    
    if parsed.hostname == 'youtu.be':
        return parsed.path.lstrip('/')
    
    return None

def http_get_dearrow_video_info(video_id, session):
    """Get the video info from Dearrow using the provided session."""
    url = f'https://sponsor.ajay.app/api/branding?videoID={video_id}'
    return http_fetch_json(session, url)

def initialize_http_session():
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=50, pool_maxsize=50)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def http_fetch_json(session, url, timeout=5):
    try:
        response = session.get(url, headers={'Connection': 'keep-alive'}, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return None

@app.route('/api/dearrow/batch', methods=['POST', 'OPTIONS'])
def get_dearrow_batch_info():
    """Process multiple YouTube video IDs in batch."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        video_ids = data.get('video_ids', [])
        
        if not video_ids:
            return jsonify({'status': 'error', 'message': 'No video IDs provided'}), 400
            
        results = {}
        session = initialize_http_session()
        
        # Process in parallel with reasonable concurrency
        # Each individual request has 5s timeout, but batch can take up to 1 minute total
        #print(f"Starting batch processing of {len(video_ids)} video IDs...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_id = {
                executor.submit(http_get_dearrow_video_info, vid, session): vid 
                for vid in video_ids
            }
            
            # Wait for all futures to complete with 60 second total timeout
            completed = 0
            for future in concurrent.futures.as_completed(future_to_id, timeout=60):
                video_id = future_to_id[future]
                completed += 1
                
                # Log progress every 50 items
                if completed % 50 == 0:
                    print(f"Processed {completed}/{len(video_ids)} videos...")
                
                try:
                    result = future.result()
                    if result:
                        results[video_id] = result
                    # If no result, just skip it (silent failure as requested)
                except Exception as e:
                    # Log error but continue processing other videos
                    print(f"Error processing video {video_id}: {e}")
                    continue
        
       #print(f"Batch processing complete. Successfully processed {len(results)}/{len(video_ids)} videos.")
        return jsonify({
            'status': 'success',
            'data': results,
            'processed': len(video_ids),
            'successful': len(results)
        })
        
    except concurrent.futures.TimeoutError:
        print("Batch processing timed out after 60 seconds")
        return jsonify({'status': 'error', 'message': 'Batch processing timed out'}), 408
    except Exception as e:
        print(f"Error in batch processing: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)  # Using port 5001 to avoid conflict with the original server 
