"""
Pinterest iOS App Artifact Parser
Extracts Pinterest app data including search history, user profiles, boards, pins, and cached content
"""

import json
import os
import sqlite3
import plistlib
from pathlib import Path
from datetime import datetime

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
    "pinterestSearchHistory": {
        "name": "Pinterest - Search History",
        "description": "Extracts Pinterest search history including search queries and relevance scores",
        "author": "@js-forensics",
        "creation_date": "2025-01-17",
        "last_update_date": "2025-01-17",
        "requirements": "none",
        "category": "Pinterest",
        "notes": "Parses Pinterest search database containing user search queries",
        "paths": (
            '*/Documents/*ap.db',
            '*/Documents/*ap.db-*',
        ),
        "output_types": "all",
        "artifact_icon": "search"
    },
    "pinterestUserProfile": {
        "name": "Pinterest - User Profile",
        "description": "Extracts Pinterest user profile information including username, full name, and account details",
        "author": "@js-forensics",
        "creation_date": "2025-01-17",
        "last_update_date": "2025-01-17",
        "requirements": "none",
        "category": "Pinterest",
        "notes": "Parses Pinterest user profile data from activeUser files",
        "paths": (
            '*/Documents/activeUser*',
        ),
        "output_types": "all",
        "artifact_icon": "user"
    },
    "pinterestNetworkActivity": {
        "name": "Pinterest - Network Activity",
        "description": "Extracts Pinterest network activity including cached requests and timestamps",
        "author": "@js-forensics",
        "creation_date": "2025-01-17",
        "last_update_date": "2025-01-17",
        "requirements": "none",
        "category": "Pinterest",
        "notes": "Parses Pinterest network cache database for web requests",
        "paths": (
            '*/Library/Caches/pinterest/Cache.db',
            '*/Library/Caches/pinterest/Cache.db-*',
        ),
        "output_types": "all",
        "artifact_icon": "activity"
    },
    "pinterestPreferences": {
        "name": "Pinterest - Preferences",
        "description": "Extracts Pinterest app preferences and configuration settings",
        "author": "@js-forensics",
        "creation_date": "2025-01-17",
        "last_update_date": "2025-01-17",
        "requirements": "none",
        "category": "Pinterest",
        "notes": "Parses Pinterest app preferences plist file",
        "paths": (
            '*/Library/Preferences/pinterest.plist',
        ),
        "output_types": "all",
        "artifact_icon": "settings"
    }
}

def parse_pinterest_search_db(db_path):
    """Parse Pinterest search history from FTS database"""
    data_list = []
    
    try:
        if not does_table_exist_in_db(db_path, 'search_queries'):
            return data_list
            
        query = '''
            SELECT 
                query,
                score
            FROM search_queries
            ORDER BY score DESC
        '''
        
        db_records = get_sqlite_db_records(db_path, query)
        
        for record in db_records:
            try:
                search_query = record['query'] if record['query'] else ''
                relevance_score = record['score'] if record['score'] else 0.0
                
                data_list.append((
                    search_query,
                    str(relevance_score),
                    db_path
                ))
                
            except Exception as e:
                logfunc(f"Error processing search record: {str(e)}")
                continue
                
    except Exception as e:
        logfunc(f"Error processing Pinterest search database {db_path}: {str(e)}")
    
    return data_list

def parse_pinterest_user_profile(file_path):
    """Parse Pinterest user profile from activeUser plist files"""
    data_list = []
    
    try:
        with open(file_path, 'rb') as file:
            plist_data = plistlib.load(file)
            
        file_name = os.path.basename(file_path)
        
        # Extract user information from the plist structure
        if isinstance(plist_data, dict):
            # Look for common user profile fields
            user_id = ''
            username = ''
            full_name = ''
            profile_image = ''
            
            # Try to find user data in various plist structures
            def extract_user_data(data, prefix=''):
                nonlocal user_id, username, full_name, profile_image
                
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, (str, int)) and value:
                            key_lower = key.lower()
                            if 'userid' in key_lower or 'user_id' in key_lower:
                                user_id = str(value)
                            elif 'username' in key_lower:
                                username = str(value)
                            elif 'fullname' in key_lower or 'full_name' in key_lower:
                                full_name = str(value)
                            elif 'profile' in key_lower and 'image' in key_lower:
                                profile_image = str(value)
                            elif 'avatar' in key_lower:
                                profile_image = str(value)
                        elif isinstance(value, dict):
                            extract_user_data(value, f"{prefix}{key}.")
                        elif isinstance(value, list):
                            for i, item in enumerate(value):
                                if isinstance(item, dict):
                                    extract_user_data(item, f"{prefix}{key}[{i}].")
            
            extract_user_data(plist_data)
            
            # Add general entry for the profile file
            data_list.append((
                '',  # timestamp
                'User Profile',
                file_name,
                user_id,
                username,
                full_name,
                profile_image,
                file_path
            ))
            
            # Add entries for significant keys found in the plist
            for key, value in plist_data.items():
                if isinstance(value, (str, int, float)) and len(str(value)) < 200:
                    data_list.append((
                        '',  # timestamp
                        'Profile Data',
                        key,
                        str(value),
                        '',  # field4
                        '',  # field5
                        '',  # field6
                        file_path
                    ))
            
    except Exception as e:
        logfunc(f"Error parsing Pinterest user profile file {file_path}: {str(e)}")
    
    return data_list

def parse_pinterest_network_cache(db_path):
    """Parse Pinterest network activity from Cache.db"""
    data_list = []
    
    try:
        if not does_table_exist_in_db(db_path, 'cfurl_cache_response'):
            return data_list
            
        query = '''
            SELECT 
                r.request_key,
                r.time_stamp,
                r.storage_policy,
                r.partition,
                b.response_object,
                d.receiver_data
            FROM cfurl_cache_response r
            LEFT JOIN cfurl_cache_blob_data b ON r.entry_ID = b.entry_ID
            LEFT JOIN cfurl_cache_receiver_data d ON r.entry_ID = d.entry_ID
            ORDER BY r.time_stamp DESC
            LIMIT 500
        '''
        
        db_records = get_sqlite_db_records(db_path, query)
        
        for record in db_records:
            try:
                request_key = record['request_key'] if record['request_key'] else ''
                timestamp = record['time_stamp'] if record['time_stamp'] else 0
                storage_policy = record['storage_policy'] if record['storage_policy'] else 0
                partition = record['partition'] if record['partition'] else ''
                response_object = record['response_object'] if record['response_object'] else ''
                receiver_data = record['receiver_data'] if record['receiver_data'] else ''
                
                # Convert timestamp - might be different format
                if timestamp:
                    try:
                        # Try parsing as timestamp string first
                        if isinstance(timestamp, str):
                            from datetime import datetime
                            request_time = datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
                        else:
                            request_time = convert_cocoa_core_data_ts_to_utc(timestamp)
                    except:
                        request_time = str(timestamp)
                else:
                    request_time = ''
                
                # Extract URL from request key if possible
                url = ''
                if request_key:
                    # Request key often contains the URL
                    if 'http' in request_key:
                        url = request_key
                    else:
                        url = request_key[:100]  # Truncate for display
                
                # Get response size
                response_size = len(response_object) if response_object else 0
                receiver_size = len(receiver_data) if receiver_data else 0
                total_size = response_size + receiver_size
                
                data_list.append((
                    request_time,
                    url,
                    str(total_size),
                    partition,
                    str(storage_policy),
                    request_key[:100] if request_key else '',
                    db_path
                ))
                
            except Exception as e:
                logfunc(f"Error processing network cache record: {str(e)}")
                continue
                
    except Exception as e:
        logfunc(f"Error processing Pinterest network cache database {db_path}: {str(e)}")
    
    return data_list

def parse_pinterest_preferences(file_path):
    """Parse Pinterest app preferences from plist file"""
    data_list = []
    
    try:
        with open(file_path, 'rb') as file:
            plist_data = plistlib.load(file)
            
        file_name = os.path.basename(file_path)
        
        # Extract preferences recursively
        def extract_preferences(data, prefix=''):
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, (str, int, float, bool)):
                        if len(str(value)) < 200:  # Skip very long values
                            data_list.append((
                                '',  # timestamp
                                'Preference',
                                f"{prefix}{key}",
                                str(value),
                                type(value).__name__,
                                '',  # field5
                                '',  # field6
                                file_path
                            ))
                    elif isinstance(value, dict):
                        extract_preferences(value, f"{prefix}{key}.")
                    elif isinstance(value, list):
                        for i, item in enumerate(value):
                            if isinstance(item, (str, int, float, bool)):
                                if len(str(item)) < 200:
                                    data_list.append((
                                        '',  # timestamp
                                        'Preference Array',
                                        f"{prefix}{key}[{i}]",
                                        str(item),
                                        type(item).__name__,
                                        '',  # field5
                                        '',  # field6
                                        file_path
                                    ))
                            elif isinstance(item, dict):
                                extract_preferences(item, f"{prefix}{key}[{i}].")
            
        extract_preferences(plist_data)
            
    except Exception as e:
        logfunc(f"Error parsing Pinterest preferences file {file_path}: {str(e)}")
    
    return data_list

@artifact_processor
def pinterestSearchHistory(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract Pinterest search history from search database"""
    
    data_list = []
    
    data_headers = (
        'Search Query',
        'Relevance Score',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No Pinterest search history files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing Pinterest search history file: {file_path}')
            
            if file_path.endswith('.db'):
                db_data = parse_pinterest_search_db(file_path)
                data_list.extend(db_data)
                
        except Exception as e:
            logfunc(f'Error processing Pinterest search history file {file_found}: {str(e)}')
            continue
    
    # Sort by relevance score (highest first)
    data_list.sort(key=lambda x: float(x[1]) if x[1] else 0, reverse=True)
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} Pinterest search history entries')
    
    return data_headers, data_list, source_path

@artifact_processor
def pinterestUserProfile(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract Pinterest user profile data from activeUser files"""
    
    data_list = []
    
    data_headers = (
        ('Timestamp', 'datetime'),
        'Data Type',
        'Key/Field',
        'Value/Data',
        'User ID',
        'Username',
        'Full Name',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No Pinterest user profile files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing Pinterest user profile file: {file_path}')
            
            if 'activeUser' in file_path:
                profile_data = parse_pinterest_user_profile(file_path)
                data_list.extend(profile_data)
                
        except Exception as e:
            logfunc(f'Error processing Pinterest user profile file {file_found}: {str(e)}')
            continue
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} Pinterest user profile entries')
    
    return data_headers, data_list, source_path

@artifact_processor
def pinterestNetworkActivity(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract Pinterest network activity from cache database"""
    
    data_list = []
    
    data_headers = (
        ('Request Time', 'datetime'),
        'URL',
        'Response Size (bytes)',
        'Partition',
        'Storage Policy',
        'Request Key',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No Pinterest network activity files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing Pinterest network activity file: {file_path}')
            
            if file_path.endswith('.db'):
                cache_data = parse_pinterest_network_cache(file_path)
                data_list.extend(cache_data)
                
        except Exception as e:
            logfunc(f'Error processing Pinterest network activity file {file_found}: {str(e)}')
            continue
    
    # Sort by request time (newest first)
    data_list.sort(key=lambda x: x[0] if x[0] else '', reverse=True)
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} Pinterest network activity entries')
    
    return data_headers, data_list, source_path

@artifact_processor
def pinterestPreferences(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract Pinterest app preferences from plist files"""
    
    data_list = []
    
    data_headers = (
        ('Timestamp', 'datetime'),
        'Category',
        'Key',
        'Value',
        'Data Type',
        'Field 5',
        'Field 6',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No Pinterest preferences files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing Pinterest preferences file: {file_path}')
            
            if file_path.endswith('.plist'):
                pref_data = parse_pinterest_preferences(file_path)
                data_list.extend(pref_data)
                
        except Exception as e:
            logfunc(f'Error processing Pinterest preferences file {file_found}: {str(e)}')
            continue
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} Pinterest preferences entries')
    
    return data_headers, data_list, source_path