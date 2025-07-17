"""
DuckDuckGo Privacy Browser iOS App Artifact Parser
Extracts DuckDuckGo browser data including browsing history, search history, bookmarks, and privacy settings
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
    "duckduckgoBrowserHistory": {
        "name": "DuckDuckGo Browser - History",
        "description": "Extracts DuckDuckGo browser history including visited URLs, page titles, and timestamps",
        "author": "@js-forensics",
        "creation_date": "2025-01-17",
        "last_update_date": "2025-01-17",
        "requirements": "none",
        "category": "DuckDuckGo Browser",
        "notes": "Parses DuckDuckGo History.sqlite database for browsing history",
        "paths": (
            '*/Library/WebKit/WebsiteData/LocalStorage/History.sqlite',
            '*/Library/WebKit/WebsiteData/LocalStorage/History.sqlite-*',
            '*/Documents/History.sqlite',
            '*/Documents/History.sqlite-*',
        ),
        "output_types": "all",
        "artifact_icon": "globe"
    },
    "duckduckgoBrowserBookmarks": {
        "name": "DuckDuckGo Browser - Bookmarks",
        "description": "Extracts DuckDuckGo browser bookmarks and favorites",
        "author": "@js-forensics",
        "creation_date": "2025-01-17",
        "last_update_date": "2025-01-17",
        "requirements": "none",
        "category": "DuckDuckGo Browser",
        "notes": "Parses DuckDuckGo bookmarks from various storage locations",
        "paths": (
            '*/Documents/Bookmarks.sqlite',
            '*/Documents/Bookmarks.sqlite-*',
            '*/Library/Preferences/com.duckduckgo.mobile.ios.plist',
        ),
        "output_types": "all",
        "artifact_icon": "bookmark"
    },
    "duckduckgoBrowserVault": {
        "name": "DuckDuckGo Browser - Vault",
        "description": "Extracts DuckDuckGo browser vault data (may be encrypted)",
        "author": "@js-forensics",
        "creation_date": "2025-01-17",
        "last_update_date": "2025-01-17",
        "requirements": "none",
        "category": "DuckDuckGo Browser",
        "notes": "Parses DuckDuckGo Vault.db database for secured data",
        "paths": (
            '*/Documents/Vault.db',
            '*/Documents/Vault.db-*',
            '*/Library/Application Support/Vault.db',
            '*/Library/Application Support/Vault.db-*',
        ),
        "output_types": "all",
        "artifact_icon": "lock"
    },
    "duckduckgoBrowserPreferences": {
        "name": "DuckDuckGo Browser - Preferences",
        "description": "Extracts DuckDuckGo browser preferences and privacy settings",
        "author": "@js-forensics",
        "creation_date": "2025-01-17",
        "last_update_date": "2025-01-17",
        "requirements": "none",
        "category": "DuckDuckGo Browser",
        "notes": "Parses DuckDuckGo app preferences and configuration",
        "paths": (
            '*/Library/Preferences/com.duckduckgo.mobile.ios.plist',
        ),
        "output_types": "all",
        "artifact_icon": "settings"
    }
}

def parse_duckduckgo_history(db_path):
    """Parse DuckDuckGo browsing history from History.sqlite"""
    data_list = []
    
    try:
        # Check for different possible table names
        possible_tables = ['history', 'visits', 'pages', 'browsing_history', 'web_history']
        
        for table_name in possible_tables:
            if does_table_exist_in_db(db_path, table_name):
                # Get table schema first
                schema_query = f"PRAGMA table_info({table_name})"
                schema_records = get_sqlite_db_records(db_path, schema_query)
                
                columns = [record['name'] for record in schema_records]
                
                # Build query based on available columns
                select_columns = []
                
                # Common column mappings
                column_mappings = {
                    'url': ['url', 'page_url', 'web_url', 'address'],
                    'title': ['title', 'page_title', 'name'],
                    'visit_time': ['visit_time', 'timestamp', 'date', 'time', 'created_at'],
                    'visit_count': ['visit_count', 'count', 'visits'],
                    'last_visit': ['last_visit', 'last_visit_time', 'updated_at']
                }
                
                query_parts = []
                for field, possible_cols in column_mappings.items():
                    for col in possible_cols:
                        if col in columns:
                            query_parts.append(f"{col} as {field}")
                            break
                    else:
                        query_parts.append(f"'' as {field}")
                
                query = f"SELECT {', '.join(query_parts)} FROM {table_name} ORDER BY visit_time DESC"
                
                try:
                    db_records = get_sqlite_db_records(db_path, query)
                    
                    for record in db_records:
                        url = record['url'] if record['url'] else ''
                        title = record['title'] if record['title'] else ''
                        visit_time = record['visit_time'] if record['visit_time'] else 0
                        visit_count = record['visit_count'] if record['visit_count'] else 1
                        last_visit = record['last_visit'] if record['last_visit'] else 0
                        
                        # Convert timestamps - try different formats
                        visit_timestamp = ''
                        if visit_time:
                            try:
                                if visit_time > 1000000000000:  # Milliseconds
                                    visit_timestamp = convert_unix_ts_to_utc(visit_time / 1000)
                                elif visit_time > 1000000000:  # Seconds
                                    visit_timestamp = convert_unix_ts_to_utc(visit_time)
                                else:  # Core Data timestamp
                                    visit_timestamp = convert_cocoa_core_data_ts_to_utc(visit_time)
                            except:
                                visit_timestamp = str(visit_time)
                        
                        last_visit_timestamp = ''
                        if last_visit and last_visit != visit_time:
                            try:
                                if last_visit > 1000000000000:  # Milliseconds
                                    last_visit_timestamp = convert_unix_ts_to_utc(last_visit / 1000)
                                elif last_visit > 1000000000:  # Seconds
                                    last_visit_timestamp = convert_unix_ts_to_utc(last_visit)
                                else:  # Core Data timestamp
                                    last_visit_timestamp = convert_cocoa_core_data_ts_to_utc(last_visit)
                            except:
                                last_visit_timestamp = str(last_visit)
                        
                        data_list.append((
                            visit_timestamp,
                            url,
                            title,
                            str(visit_count),
                            last_visit_timestamp,
                            table_name,
                            db_path
                        ))
                        
                except Exception as e:
                    logfunc(f"Error querying DuckDuckGo history table {table_name}: {str(e)}")
                    continue
                
                # If we found data, break out of the loop
                if data_list:
                    break
                    
    except Exception as e:
        logfunc(f"Error processing DuckDuckGo history database {db_path}: {str(e)}")
    
    return data_list

def parse_duckduckgo_bookmarks(file_path):
    """Parse DuckDuckGo bookmarks from various sources"""
    data_list = []
    
    try:
        if file_path.endswith('.sqlite'):
            # SQLite bookmarks database
            possible_tables = ['bookmarks', 'favorites', 'saved_sites']
            
            for table_name in possible_tables:
                if does_table_exist_in_db(file_path, table_name):
                    # Get table schema
                    schema_query = f"PRAGMA table_info({table_name})"
                    schema_records = get_sqlite_db_records(file_path, schema_query)
                    
                    columns = [record['name'] for record in schema_records]
                    
                    # Build query based on available columns
                    select_columns = []
                    
                    column_mappings = {
                        'url': ['url', 'bookmark_url', 'address'],
                        'title': ['title', 'bookmark_title', 'name'],
                        'created_at': ['created_at', 'date_added', 'timestamp'],
                        'folder': ['folder', 'parent', 'category']
                    }
                    
                    query_parts = []
                    for field, possible_cols in column_mappings.items():
                        for col in possible_cols:
                            if col in columns:
                                query_parts.append(f"{col} as {field}")
                                break
                        else:
                            query_parts.append(f"'' as {field}")
                    
                    query = f"SELECT {', '.join(query_parts)} FROM {table_name} ORDER BY created_at DESC"
                    
                    try:
                        db_records = get_sqlite_db_records(file_path, query)
                        
                        for record in db_records:
                            url = record['url'] if record['url'] else ''
                            title = record['title'] if record['title'] else ''
                            created_at = record['created_at'] if record['created_at'] else 0
                            folder = record['folder'] if record['folder'] else ''
                            
                            # Convert timestamp
                            created_timestamp = ''
                            if created_at:
                                try:
                                    if created_at > 1000000000000:
                                        created_timestamp = convert_unix_ts_to_utc(created_at / 1000)
                                    elif created_at > 1000000000:
                                        created_timestamp = convert_unix_ts_to_utc(created_at)
                                    else:
                                        created_timestamp = convert_cocoa_core_data_ts_to_utc(created_at)
                                except:
                                    created_timestamp = str(created_at)
                            
                            data_list.append((
                                created_timestamp,
                                title,
                                url,
                                folder,
                                'SQLite Database',
                                file_path
                            ))
                            
                    except Exception as e:
                        logfunc(f"Error querying DuckDuckGo bookmarks table {table_name}: {str(e)}")
                        continue
                    
                    if data_list:
                        break
                        
        elif file_path.endswith('.plist'):
            # Plist preferences file
            try:
                with open(file_path, 'rb') as f:
                    plist_data = plistlib.load(f)
                
                # Look for bookmark-related keys
                bookmark_keys = ['bookmarks', 'favorites', 'saved_sites', 'quick_access']
                
                for key in bookmark_keys:
                    if key in plist_data:
                        bookmarks = plist_data[key]
                        if isinstance(bookmarks, list):
                            for bookmark in bookmarks:
                                if isinstance(bookmark, dict):
                                    url = bookmark.get('url', bookmark.get('URL', ''))
                                    title = bookmark.get('title', bookmark.get('name', ''))
                                    created_at = bookmark.get('created_at', bookmark.get('date_added', ''))
                                    folder = bookmark.get('folder', bookmark.get('category', ''))
                                    
                                    data_list.append((
                                        str(created_at),
                                        title,
                                        url,
                                        folder,
                                        'Plist Preferences',
                                        file_path
                                    ))
                        elif isinstance(bookmarks, dict):
                            # Handle nested bookmark structure
                            for folder_name, folder_bookmarks in bookmarks.items():
                                if isinstance(folder_bookmarks, list):
                                    for bookmark in folder_bookmarks:
                                        if isinstance(bookmark, dict):
                                            url = bookmark.get('url', bookmark.get('URL', ''))
                                            title = bookmark.get('title', bookmark.get('name', ''))
                                            created_at = bookmark.get('created_at', bookmark.get('date_added', ''))
                                            
                                            data_list.append((
                                                str(created_at),
                                                title,
                                                url,
                                                folder_name,
                                                'Plist Preferences',
                                                file_path
                                            ))
                        
                        if data_list:
                            break
                            
            except Exception as e:
                logfunc(f"Error parsing DuckDuckGo bookmarks plist {file_path}: {str(e)}")
                
    except Exception as e:
        logfunc(f"Error processing DuckDuckGo bookmarks file {file_path}: {str(e)}")
    
    return data_list

def parse_duckduckgo_vault(db_path):
    """Parse DuckDuckGo vault database (may be encrypted)"""
    data_list = []
    
    try:
        # First check if database is encrypted
        with open(db_path, 'rb') as f:
            header = f.read(16)
            if b'SQLite format 3' not in header:
                data_list.append((
                    '',
                    'Encrypted Database',
                    'Database appears to be encrypted',
                    'Unable to parse encrypted content',
                    str(os.path.getsize(db_path)),
                    'Encrypted',
                    db_path
                ))
                return data_list
        
        # Try to get table information
        schema_query = "SELECT name FROM sqlite_master WHERE type='table'"
        
        try:
            schema_records = get_sqlite_db_records(db_path, schema_query)
            
            for table_record in schema_records:
                table_name = table_record['name']
                
                # Get row count
                count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                count_records = get_sqlite_db_records(db_path, count_query)
                row_count = count_records[0]['count'] if count_records else 0
                
                # Get table schema
                table_info_query = f"PRAGMA table_info({table_name})"
                table_info_records = get_sqlite_db_records(db_path, table_info_query)
                
                columns = [record['name'] for record in table_info_records]
                
                data_list.append((
                    '',
                    'Vault Table',
                    table_name,
                    f"Columns: {', '.join(columns)}",
                    str(row_count),
                    'Accessible',
                    db_path
                ))
                
                # Try to get sample data if possible
                if row_count > 0 and row_count < 100:  # Only for small tables
                    try:
                        sample_query = f"SELECT * FROM {table_name} LIMIT 5"
                        sample_records = get_sqlite_db_records(db_path, sample_query)
                        
                        for i, record in enumerate(sample_records):
                            sample_data = []
                            for column in columns:
                                value = record.get(column, '')
                                if isinstance(value, bytes):
                                    value = f"<binary data {len(value)} bytes>"
                                sample_data.append(f"{column}: {value}")
                            
                            data_list.append((
                                '',
                                'Sample Data',
                                f"{table_name} Row {i+1}",
                                '; '.join(sample_data),
                                '',
                                'Sample',
                                db_path
                            ))
                            
                    except Exception as e:
                        logfunc(f"Error getting sample data from vault table {table_name}: {str(e)}")
                        
        except Exception as e:
            logfunc(f"Error analyzing vault database schema: {str(e)}")
            data_list.append((
                '',
                'Database Error',
                'Unable to analyze database',
                str(e),
                str(os.path.getsize(db_path)),
                'Error',
                db_path
            ))
            
    except Exception as e:
        logfunc(f"Error processing DuckDuckGo vault database {db_path}: {str(e)}")
    
    return data_list

def parse_duckduckgo_preferences(file_path):
    """Parse DuckDuckGo preferences from plist file"""
    data_list = []
    
    try:
        with open(file_path, 'rb') as f:
            plist_data = plistlib.load(f)
        
        # Recursively extract preferences
        def extract_preferences(data, prefix=''):
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, (str, int, float, bool)):
                        if len(str(value)) < 500:  # Skip very long values
                            data_list.append((
                                '',
                                'Preference',
                                f"{prefix}{key}",
                                str(value),
                                type(value).__name__,
                                '',
                                file_path
                            ))
                    elif isinstance(value, dict):
                        extract_preferences(value, f"{prefix}{key}.")
                    elif isinstance(value, list):
                        for i, item in enumerate(value):
                            if isinstance(item, (str, int, float, bool)):
                                if len(str(item)) < 500:
                                    data_list.append((
                                        '',
                                        'Preference Array',
                                        f"{prefix}{key}[{i}]",
                                        str(item),
                                        type(item).__name__,
                                        '',
                                        file_path
                                    ))
                            elif isinstance(item, dict):
                                extract_preferences(item, f"{prefix}{key}[{i}].")
            
        extract_preferences(plist_data)
        
    except Exception as e:
        logfunc(f"Error parsing DuckDuckGo preferences file {file_path}: {str(e)}")
    
    return data_list

@artifact_processor
def duckduckgoBrowserHistory(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract DuckDuckGo browser history"""
    
    data_list = []
    
    data_headers = (
        ('Visit Time', 'datetime'),
        'URL',
        'Title',
        'Visit Count',
        ('Last Visit', 'datetime'),
        'Source Table',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No DuckDuckGo browser history files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing DuckDuckGo browser history file: {file_path}')
            
            if file_path.endswith('.sqlite'):
                history_data = parse_duckduckgo_history(file_path)
                data_list.extend(history_data)
                
        except Exception as e:
            logfunc(f'Error processing DuckDuckGo browser history file {file_found}: {str(e)}')
            continue
    
    # Sort by visit time (newest first)
    data_list.sort(key=lambda x: x[0] if x[0] else '', reverse=True)
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} DuckDuckGo browser history entries')
    
    return data_headers, data_list, source_path

@artifact_processor
def duckduckgoBrowserBookmarks(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract DuckDuckGo browser bookmarks"""
    
    data_list = []
    
    data_headers = (
        ('Created', 'datetime'),
        'Title',
        'URL',
        'Folder',
        'Source Type',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No DuckDuckGo browser bookmark files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing DuckDuckGo browser bookmark file: {file_path}')
            
            bookmark_data = parse_duckduckgo_bookmarks(file_path)
            data_list.extend(bookmark_data)
                
        except Exception as e:
            logfunc(f'Error processing DuckDuckGo browser bookmark file {file_found}: {str(e)}')
            continue
    
    # Sort by created time (newest first)
    data_list.sort(key=lambda x: x[0] if x[0] else '', reverse=True)
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} DuckDuckGo browser bookmark entries')
    
    return data_headers, data_list, source_path

@artifact_processor
def duckduckgoBrowserVault(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract DuckDuckGo browser vault data"""
    
    data_list = []
    
    data_headers = (
        ('Timestamp', 'datetime'),
        'Data Type',
        'Name/Table',
        'Content/Description',
        'Size/Count',
        'Status',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No DuckDuckGo browser vault files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing DuckDuckGo browser vault file: {file_path}')
            
            if file_path.endswith('.db'):
                vault_data = parse_duckduckgo_vault(file_path)
                data_list.extend(vault_data)
                
        except Exception as e:
            logfunc(f'Error processing DuckDuckGo browser vault file {file_found}: {str(e)}')
            continue
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} DuckDuckGo browser vault entries')
    
    return data_headers, data_list, source_path

@artifact_processor
def duckduckgoBrowserPreferences(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract DuckDuckGo browser preferences"""
    
    data_list = []
    
    data_headers = (
        ('Timestamp', 'datetime'),
        'Category',
        'Key',
        'Value',
        'Data Type',
        'Additional Info',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No DuckDuckGo browser preference files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing DuckDuckGo browser preference file: {file_path}')
            
            if file_path.endswith('.plist'):
                pref_data = parse_duckduckgo_preferences(file_path)
                data_list.extend(pref_data)
                
        except Exception as e:
            logfunc(f'Error processing DuckDuckGo browser preference file {file_found}: {str(e)}')
            continue
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} DuckDuckGo browser preference entries')
    
    return data_headers, data_list, source_path