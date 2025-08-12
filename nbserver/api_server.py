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

# Test database connection immediately
get_db()

@app.route('/')
def index():
    """Serve the frontend application."""
    return render_template('index.html')

def get_non_deleted_items():
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
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
                rss_item.feedurl
            FROM
                rss_item
            INNER JOIN
                rss_feed ON rss_item.feedurl = rss_feed.rssurl
                WHERE deleted = 0
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
                'feedurl': row['feedurl']
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
                feedurl
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
            'feedurl': row['feedurl']
        }
    except Exception as e:
        print(f"Error in get_item_by_id: {str(e)}")
        return None

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
    """Toggle the unread flag for an item in the database, simplified."""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Toggle unread: unread = 1 -> 0, unread = 0 -> 1
        cursor.execute("""
            UPDATE rss_item
            SET unread = CASE unread WHEN 0 THEN 1 ELSE 0 END
            WHERE id = ? AND deleted = 0
        """, (item_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        
        if not success:
            return None

        # Get the new unread value
        cursor.execute("SELECT unread FROM rss_item WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        return row['unread'] if row else None
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
        return jsonify({
            'status': 'success',
            'message': 'Unread status updated successfully',
            'data': {'unread': new_unread}
        })
    return jsonify({
        'status': 'error',
        'message': 'Item not found or failed to update'
    }), 404

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

# business logic
def process_items(items):
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


if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Using port 5001 to avoid conflict with the original server 