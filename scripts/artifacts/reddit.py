"""
Reddit iOS App Artifact Parser
Extracts Reddit app data including user profiles, posts, comments, messages, and browsing history
"""

import json
import os
import sqlite3
from pathlib import Path

from scripts.ilapfuncs import (
    artifact_processor,
    get_file_path,
    get_sqlite_db_records,
    convert_unix_ts_to_utc,
    convert_cocoa_core_data_ts_to_utc,
    logfunc,
    does_table_exist_in_db
)

__artifacts_v2__ = {
    "redditAppData": {
        "name": "Reddit - App Data",
        "description": "Extracts Reddit app data including user profiles, posts, comments, messages, and browsing history",
        "author": "@js-forensics",
        "creation_date": "2025-01-17",
        "last_update_date": "2025-01-17",
        "requirements": "none",
        "category": "Reddit",
        "notes": "Parses Reddit app SQLite databases, JSON caches, and preference files",
        "paths": (
            '*/com.reddit.Reddit/Documents/*',
            '*/com.reddit.Reddit/Library/Caches/*',
            '*/com.reddit.Reddit/Library/Application Support/*',
            '*/com.reddit.Reddit/Library/Preferences/*',
            '*/group.com.reddit.Reddit.plist',
            '*/com.reddit.Reddit*.sqlite*',
            '*/com.reddit.Reddit*.db',
            '*/iCloud.com.reddit.reddit*'
        ),
        "output_types": "all",
        "artifact_icon": "message-square"
    }
}

def parse_reddit_sqlite_db(db_path):
    """Parse Reddit SQLite database and extract forensically relevant data"""
    data_list = []
    
    try:
        # Check if common Reddit tables exist
        if does_table_exist_in_db(db_path, 'posts'):
            query = '''
                SELECT 
                    id,
                    title,
                    author,
                    subreddit,
                    created_utc,
                    score,
                    num_comments,
                    url,
                    selftext,
                    thumbnail
                FROM posts
                ORDER BY created_utc DESC
            '''
            db_records = get_sqlite_db_records(db_path, query)
            
            for record in db_records:
                try:
                    timestamp = convert_unix_ts_to_utc(record['created_utc']) if record['created_utc'] else ''
                    data_list.append((
                        timestamp,
                        record['title'] or '',
                        record['author'] or '',
                        record['subreddit'] or '',
                        record['score'] or 0,
                        record['num_comments'] or 0,
                        record['url'] or '',
                        record['selftext'] or '',
                        record['thumbnail'] or '',
                        'Posts',
                        db_path
                    ))
                except Exception as e:
                    logfunc(f"Error processing post record: {str(e)}")
                    continue
        
        if does_table_exist_in_db(db_path, 'comments'):
            query = '''
                SELECT 
                    id,
                    post_id,
                    author,
                    body,
                    created_utc,
                    score,
                    parent_id,
                    subreddit
                FROM comments
                ORDER BY created_utc DESC
            '''
            db_records = get_sqlite_db_records(db_path, query)
            
            for record in db_records:
                try:
                    timestamp = convert_unix_ts_to_utc(record['created_utc']) if record['created_utc'] else ''
                    data_list.append((
                        timestamp,
                        record['post_id'] or '',
                        record['author'] or '',
                        record['subreddit'] or '',
                        record['score'] or 0,
                        '',  # num_comments not applicable
                        '',  # url not applicable
                        record['body'] or '',
                        '',  # thumbnail not applicable
                        'Comments',
                        db_path
                    ))
                except Exception as e:
                    logfunc(f"Error processing comment record: {str(e)}")
                    continue
        
        if does_table_exist_in_db(db_path, 'messages'):
            query = '''
                SELECT 
                    id,
                    author,
                    dest,
                    body,
                    created_utc,
                    subject,
                    was_comment
                FROM messages
                ORDER BY created_utc DESC
            '''
            db_records = get_sqlite_db_records(db_path, query)
            
            for record in db_records:
                try:
                    timestamp = convert_unix_ts_to_utc(record['created_utc']) if record['created_utc'] else ''
                    message_type = 'Comment Reply' if record['was_comment'] else 'Private Message'
                    data_list.append((
                        timestamp,
                        record['subject'] or '',
                        record['author'] or '',
                        record['dest'] or '',
                        0,  # score not applicable
                        0,  # num_comments not applicable
                        '',  # url not applicable
                        record['body'] or '',
                        '',  # thumbnail not applicable
                        message_type,
                        db_path
                    ))
                except Exception as e:
                    logfunc(f"Error processing message record: {str(e)}")
                    continue
        
        if does_table_exist_in_db(db_path, 'users'):
            query = '''
                SELECT 
                    name,
                    created_utc,
                    link_karma,
                    comment_karma,
                    has_verified_email,
                    is_gold,
                    is_mod,
                    subreddit
                FROM users
                ORDER BY created_utc DESC
            '''
            db_records = get_sqlite_db_records(db_path, query)
            
            for record in db_records:
                try:
                    timestamp = convert_unix_ts_to_utc(record['created_utc']) if record['created_utc'] else ''
                    user_info = f"Link Karma: {record['link_karma']}, Comment Karma: {record['comment_karma']}"
                    if record['has_verified_email']:
                        user_info += ", Verified Email"
                    if record['is_gold']:
                        user_info += ", Gold Member"
                    if record['is_mod']:
                        user_info += ", Moderator"
                    
                    data_list.append((
                        timestamp,
                        record['name'] or '',
                        record['name'] or '',
                        record['subreddit'] or '',
                        record['link_karma'] or 0,
                        record['comment_karma'] or 0,
                        '',  # url not applicable
                        user_info,
                        '',  # thumbnail not applicable
                        'User Profile',
                        db_path
                    ))
                except Exception as e:
                    logfunc(f"Error processing user record: {str(e)}")
                    continue
                    
    except Exception as e:
        logfunc(f"Error processing Reddit database {db_path}: {str(e)}")
    
    return data_list

def parse_reddit_json_cache(json_path):
    """Parse Reddit JSON cache files"""
    data_list = []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            json_data = json.load(file)
            
        if isinstance(json_data, dict):
            # Handle API response format
            if 'data' in json_data and 'children' in json_data['data']:
                for child in json_data['data']['children']:
                    if 'data' in child:
                        item = child['data']
                        try:
                            timestamp = convert_unix_ts_to_utc(item.get('created_utc', 0))
                            data_list.append((
                                timestamp,
                                item.get('title', item.get('body', '')),
                                item.get('author', ''),
                                item.get('subreddit', ''),
                                item.get('score', 0),
                                item.get('num_comments', 0),
                                item.get('url', ''),
                                item.get('selftext', item.get('body', '')),
                                item.get('thumbnail', ''),
                                'JSON Cache',
                                json_path
                            ))
                        except Exception as e:
                            logfunc(f"Error processing JSON item: {str(e)}")
                            continue
            
            # Handle other JSON structures
            elif 'posts' in json_data:
                for post in json_data['posts']:
                    try:
                        timestamp = convert_unix_ts_to_utc(post.get('created_utc', 0))
                        data_list.append((
                            timestamp,
                            post.get('title', ''),
                            post.get('author', ''),
                            post.get('subreddit', ''),
                            post.get('score', 0),
                            post.get('num_comments', 0),
                            post.get('url', ''),
                            post.get('selftext', ''),
                            post.get('thumbnail', ''),
                            'JSON Cache',
                            json_path
                        ))
                    except Exception as e:
                        logfunc(f"Error processing JSON post: {str(e)}")
                        continue
                        
    except Exception as e:
        logfunc(f"Error parsing Reddit JSON file {json_path}: {str(e)}")
    
    return data_list

def parse_reddit_preferences(plist_path):
    """Parse Reddit app preferences and configuration"""
    data_list = []
    
    try:
        import plistlib
        
        with open(plist_path, 'rb') as file:
            plist_data = plistlib.load(file)
            
        # Extract relevant preference data
        timestamp = ''
        if 'lastUpdateCheck' in plist_data:
            timestamp = convert_unix_ts_to_utc(plist_data['lastUpdateCheck'])
        
        prefs_info = []
        for key, value in plist_data.items():
            if key in ['username', 'userID', 'accessToken', 'refreshToken', 'lastLogin', 'notifications', 'theme', 'language']:
                if key in ['accessToken', 'refreshToken']:
                    # Don't log sensitive tokens fully
                    prefs_info.append(f"{key}: {'*' * 20}")
                else:
                    prefs_info.append(f"{key}: {value}")
        
        if prefs_info:
            data_list.append((
                timestamp,
                'App Preferences',
                plist_data.get('username', ''),
                '',
                0,
                0,
                '',
                '; '.join(prefs_info),
                '',
                'Preferences',
                plist_path
            ))
            
    except Exception as e:
        logfunc(f"Error parsing Reddit preferences {plist_path}: {str(e)}")
    
    return data_list

@artifact_processor
def redditAppData(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract Reddit app data from iOS extraction"""
    
    data_list = []
    
    # Define data headers with type hints
    data_headers = (
        ('Timestamp', 'datetime'),
        'Title/Content',
        'Author/User',
        'Subreddit/Destination',
        'Score/Link Karma',
        'Comments/Comment Karma',
        'URL',
        'Text/Body',
        'Thumbnail',
        'Data Type',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No Reddit app files found')
        return data_headers, data_list, ''
    
    # Process each file found
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing Reddit file: {file_path}')
            
            # Handle SQLite databases
            if file_path.endswith('.sqlite') or file_path.endswith('.db'):
                sqlite_data = parse_reddit_sqlite_db(file_path)
                data_list.extend(sqlite_data)
            
            # Handle JSON cache files
            elif file_path.endswith('.json'):
                json_data = parse_reddit_json_cache(file_path)
                data_list.extend(json_data)
            
            # Handle plist files
            elif file_path.endswith('.plist'):
                plist_data = parse_reddit_preferences(file_path)
                data_list.extend(plist_data)
            
            # Handle other file types
            else:
                # Check if file might be a database without extension
                try:
                    if os.path.getsize(file_path) > 0:
                        # Try to open as SQLite
                        conn = sqlite3.connect(file_path)
                        cursor = conn.cursor()
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                        tables = cursor.fetchall()
                        conn.close()
                        
                        if tables:
                            logfunc(f'Found SQLite database without extension: {file_path}')
                            sqlite_data = parse_reddit_sqlite_db(file_path)
                            data_list.extend(sqlite_data)
                        
                except Exception:
                    # Not a SQLite database, continue
                    pass
                    
        except Exception as e:
            logfunc(f'Error processing Reddit file {file_found}: {str(e)}')
            continue
    
    # Sort data by timestamp (newest first)
    data_list.sort(key=lambda x: x[0] if x[0] else '', reverse=True)
    
    # Get source path for display
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} Reddit app data entries')
    
    return data_headers, data_list, source_path