"""
AppLock Security App iOS Artifact Parser
Extracts protected media albums, secure files, and app configuration from AppLock
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
    logfunc,
    does_table_exist_in_db
)

__artifacts_v2__ = {
    "applockProtectedAlbums": {
        "name": "AppLock - Protected Albums",
        "description": "Extracts protected photo/video albums from AppLock security app",
        "author": "@js-forensics",
        "creation_date": "2025-07-17",
        "last_update_date": "2025-07-17",
        "requirements": "none",
        "category": "AppLock Security",
        "notes": "Parses AppLock.db for protected media albums and organization",
        "paths": (
            '*/Documents/AppLock.db',
            '*/Documents/AppLock.db-*',
        ),
        "output_types": "all",
        "artifact_icon": "folder-lock"
    },
    "applockProtectedMedia": {
        "name": "AppLock - Protected Media",
        "description": "Extracts protected media files and metadata from AppLock security app",
        "author": "@js-forensics",
        "creation_date": "2025-07-17",
        "last_update_date": "2025-07-17",
        "requirements": "none",
        "category": "AppLock Security",
        "notes": "Parses AppLock.db for protected media files and their metadata",
        "paths": (
            '*/Documents/AppLock.db',
            '*/Documents/AppLock.db-*',
        ),
        "output_types": "all",
        "artifact_icon": "file-lock"
    },
    "applockVaultConfig": {
        "name": "AppLock - Vault Configuration",
        "description": "Extracts media vault configuration and file mappings from AppLock",
        "author": "@js-forensics",
        "creation_date": "2025-07-17",
        "last_update_date": "2025-07-17",
        "requirements": "none",
        "category": "AppLock Security",
        "notes": "Parses vault media config files for file mappings",
        "paths": (
            '*/Documents/Vault/Medias/*/config.kv',
        ),
        "output_types": "all",
        "artifact_icon": "vault"
    },
    "applockPreferences": {
        "name": "AppLock - Preferences",
        "description": "Extracts AppLock app preferences and security settings",
        "author": "@js-forensics",
        "creation_date": "2025-07-17",
        "last_update_date": "2025-07-17",
        "requirements": "none",
        "category": "AppLock Security",
        "notes": "Parses app preferences plist for security and usage settings",
        "paths": (
            '*/Library/Preferences/com.domobile.applock.plist',
        ),
        "output_types": "all",
        "artifact_icon": "settings"
    },
    "applockBookmarks": {
        "name": "AppLock - Protected Bookmarks",
        "description": "Extracts protected web bookmarks from AppLock security app",
        "author": "@js-forensics",
        "creation_date": "2025-07-17",
        "last_update_date": "2025-07-17",
        "requirements": "none",
        "category": "AppLock Security",
        "notes": "Parses AppLock.db for protected web bookmarks",
        "paths": (
            '*/Documents/AppLock.db',
            '*/Documents/AppLock.db-*',
        ),
        "output_types": "all",
        "artifact_icon": "bookmark-lock"
    }
}

def parse_applock_albums(db_path):
    """Parse AppLock protected albums from AppLock.db"""
    data_list = []
    
    try:
        if not does_table_exist_in_db(db_path, 'sAlbum'):
            return data_list
            
        query = """
        SELECT 
            _id,
            albumId,
            name,
            mediaId,
            lastTime,
            attach,
            sort
        FROM sAlbum
        ORDER BY lastTime DESC
        """
        
        db_records = get_sqlite_db_records(db_path, query)
        
        for record in db_records:
            album_id = record['_id'] if record['_id'] else ''
            album_uid = record['albumId'] if record['albumId'] else ''
            album_name = record['name'] if record['name'] else ''
            media_id = record['mediaId'] if record['mediaId'] else ''
            last_time = record['lastTime'] if record['lastTime'] else 0
            attach = record['attach'] if record['attach'] else ''
            sort_order = record['sort'] if record['sort'] else 0
            
            # Convert timestamp from milliseconds
            last_time_str = ''
            if last_time:
                try:
                    last_time_str = convert_unix_ts_to_utc(last_time / 1000)
                except:
                    last_time_str = str(last_time)
            
            data_list.append((
                last_time_str,
                album_name,
                album_uid,
                str(album_id),
                media_id,
                attach,
                str(sort_order),
                db_path
            ))
            
    except Exception as e:
        logfunc(f"Error parsing AppLock albums: {str(e)}")
    
    return data_list

def parse_applock_media(db_path):
    """Parse AppLock protected media from AppLock.db"""
    data_list = []
    
    try:
        if not does_table_exist_in_db(db_path, 'sMedia'):
            return data_list
            
        query = """
        SELECT 
            _id,
            mediaId,
            albumId,
            mimeType,
            srcAlbum,
            srcSmart,
            fileName,
            fileSize,
            width,
            height,
            duration,
            fromId,
            lastTime,
            lastModified,
            attach,
            sort
        FROM sMedia
        ORDER BY lastTime DESC
        """
        
        db_records = get_sqlite_db_records(db_path, query)
        
        for record in db_records:
            media_id = record['_id'] if record['_id'] else ''
            media_uid = record['mediaId'] if record['mediaId'] else ''
            album_id = record['albumId'] if record['albumId'] else ''
            mime_type = record['mimeType'] if record['mimeType'] else ''
            src_album = record['srcAlbum'] if record['srcAlbum'] else ''
            src_smart = record['srcSmart'] if record['srcSmart'] else 0
            file_name = record['fileName'] if record['fileName'] else ''
            file_size = record['fileSize'] if record['fileSize'] else 0
            width = record['width'] if record['width'] else 0
            height = record['height'] if record['height'] else 0
            duration = record['duration'] if record['duration'] else ''
            from_id = record['fromId'] if record['fromId'] else 0
            last_time = record['lastTime'] if record['lastTime'] else 0
            last_modified = record['lastModified'] if record['lastModified'] else 0
            attach = record['attach'] if record['attach'] else ''
            sort_order = record['sort'] if record['sort'] else 0
            
            # Convert timestamps from milliseconds
            last_time_str = ''
            if last_time:
                try:
                    last_time_str = convert_unix_ts_to_utc(last_time / 1000)
                except:
                    last_time_str = str(last_time)
            
            last_modified_str = ''
            if last_modified and last_modified != last_time:
                try:
                    last_modified_str = convert_unix_ts_to_utc(last_modified / 1000)
                except:
                    last_modified_str = str(last_modified)
            
            # Format dimensions
            dimensions = ''
            if width and height:
                dimensions = f"{width}x{height}"
            
            data_list.append((
                last_time_str,
                file_name,
                media_uid,
                album_id,
                mime_type,
                dimensions,
                f"{file_size:,}" if file_size else '',
                duration,
                last_modified_str,
                src_album,
                str(src_smart),
                str(from_id),
                attach,
                str(sort_order),
                db_path
            ))
            
    except Exception as e:
        logfunc(f"Error parsing AppLock media: {str(e)}")
    
    return data_list

def parse_applock_bookmarks(db_path):
    """Parse AppLock protected bookmarks from AppLock.db"""
    data_list = []
    
    try:
        if not does_table_exist_in_db(db_path, 'web_bookmarks'):
            return data_list
            
        query = """
        SELECT 
            _id,
            bookmarkId,
            url,
            name,
            lastTime,
            sort
        FROM web_bookmarks
        ORDER BY lastTime DESC
        """
        
        db_records = get_sqlite_db_records(db_path, query)
        
        for record in db_records:
            bookmark_id = record['_id'] if record['_id'] else ''
            bookmark_uid = record['bookmarkId'] if record['bookmarkId'] else ''
            url = record['url'] if record['url'] else ''
            name = record['name'] if record['name'] else ''
            last_time = record['lastTime'] if record['lastTime'] else 0
            sort_order = record['sort'] if record['sort'] else ''
            
            # Convert timestamp from milliseconds
            last_time_str = ''
            if last_time:
                try:
                    last_time_str = convert_unix_ts_to_utc(last_time / 1000)
                except:
                    last_time_str = str(last_time)
            
            data_list.append((
                last_time_str,
                name,
                url,
                bookmark_uid,
                str(bookmark_id),
                sort_order,
                db_path
            ))
            
    except Exception as e:
        logfunc(f"Error parsing AppLock bookmarks: {str(e)}")
    
    return data_list

def parse_applock_vault_config(file_path):
    """Parse AppLock vault configuration files"""
    data_list = []
    
    try:
        # Extract vault folder timestamp from path
        vault_folder = Path(file_path).parent.name
        
        try:
            vault_timestamp = int(vault_folder) / 1000000  # Convert from microseconds
            vault_time_str = convert_unix_ts_to_utc(vault_timestamp)
        except:
            vault_time_str = vault_folder
        
        # Parse the plist configuration
        with open(file_path, 'rb') as f:
            config_data = plistlib.load(f)
        
        # Extract media mappings
        for key, value in config_data.items():
            if isinstance(value, str):
                data_list.append((
                    vault_time_str,
                    'Media Mapping',
                    f"ID {key}",
                    value,
                    vault_folder,
                    str(os.path.getsize(file_path)),
                    file_path
                ))
        
        # If no mappings found, record the vault folder existence
        if not data_list:
            data_list.append((
                vault_time_str,
                'Vault Folder',
                vault_folder,
                'Empty configuration',
                '',
                str(os.path.getsize(file_path)),
                file_path
            ))
            
    except Exception as e:
        logfunc(f"Error parsing AppLock vault config {file_path}: {str(e)}")
        # Record error but include file info
        data_list.append((
            '',
            'Config Error',
            Path(file_path).parent.name,
            str(e),
            '',
            str(os.path.getsize(file_path) if os.path.exists(file_path) else 0),
            file_path
        ))
    
    return data_list

def parse_applock_preferences(file_path):
    """Parse AppLock preferences plist"""
    data_list = []
    
    try:
        with open(file_path, 'rb') as f:
            plist_data = plistlib.load(f)
        
        # Recursively extract preferences
        def extract_preferences(data, prefix=''):
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, (str, int, float, bool)):
                        # Convert value to string and truncate if too long
                        value_str = str(value)
                        if len(value_str) > 200:
                            value_str = value_str[:200] + '...'
                        
                        # Categorize the preference
                        category = 'General'
                        if 'password' in key.lower():
                            category = 'Security'
                        elif 'privacy' in key.lower():
                            category = 'Privacy'
                        elif 'ad' in key.lower() or 'sdk' in key.lower():
                            category = 'Advertising'
                        elif 'time' in key.lower():
                            category = 'Timing'
                        elif 'session' in key.lower():
                            category = 'Session'
                        
                        data_list.append((
                            '',
                            category,
                            f"{prefix}{key}",
                            value_str,
                            type(value).__name__,
                            '',
                            file_path
                        ))
                    elif isinstance(value, dict):
                        extract_preferences(value, f"{prefix}{key}.")
                    elif isinstance(value, list):
                        for i, item in enumerate(value):
                            if isinstance(item, (str, int, float, bool)):
                                item_str = str(item)
                                if len(item_str) > 200:
                                    item_str = item_str[:200] + '...'
                                
                                data_list.append((
                                    '',
                                    'Array',
                                    f"{prefix}{key}[{i}]",
                                    item_str,
                                    type(item).__name__,
                                    '',
                                    file_path
                                ))
                            elif isinstance(item, dict):
                                extract_preferences(item, f"{prefix}{key}[{i}].")
        
        extract_preferences(plist_data)
        
    except Exception as e:
        logfunc(f"Error parsing AppLock preferences {file_path}: {str(e)}")
    
    return data_list

@artifact_processor
def applockProtectedAlbums(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract AppLock protected albums"""
    
    data_list = []
    
    data_headers = (
        ('Last Modified', 'datetime'),
        'Album Name',
        'Album ID',
        'Internal ID',
        'Media ID',
        'Attachment',
        'Sort Order',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No AppLock database files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing AppLock albums file: {file_path}')
            
            if file_path.endswith('.db'):
                albums_data = parse_applock_albums(file_path)
                data_list.extend(albums_data)
                
        except Exception as e:
            logfunc(f'Error processing AppLock albums file {file_found}: {str(e)}')
            continue
    
    # Sort by last modified time (newest first)
    data_list.sort(key=lambda x: x[0] if x[0] else '', reverse=True)
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} AppLock protected albums')
    
    return data_headers, data_list, source_path

@artifact_processor
def applockProtectedMedia(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract AppLock protected media"""
    
    data_list = []
    
    data_headers = (
        ('Last Modified', 'datetime'),
        'File Name',
        'Media ID',
        'Album ID',
        'MIME Type',
        'Dimensions',
        'File Size',
        'Duration',
        ('Modified Date', 'datetime'),
        'Source Album',
        'Smart Source',
        'From ID',
        'Attachment',
        'Sort Order',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No AppLock database files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing AppLock media file: {file_path}')
            
            if file_path.endswith('.db'):
                media_data = parse_applock_media(file_path)
                data_list.extend(media_data)
                
        except Exception as e:
            logfunc(f'Error processing AppLock media file {file_found}: {str(e)}')
            continue
    
    # Sort by last modified time (newest first)
    data_list.sort(key=lambda x: x[0] if x[0] else '', reverse=True)
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} AppLock protected media entries')
    
    return data_headers, data_list, source_path

@artifact_processor
def applockVaultConfig(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract AppLock vault configuration"""
    
    data_list = []
    
    data_headers = (
        ('Vault Created', 'datetime'),
        'Data Type',
        'Media ID',
        'File Name',
        'Vault Folder',
        'Config Size',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No AppLock vault config files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing AppLock vault config file: {file_path}')
            
            if file_path.endswith('.kv'):
                vault_data = parse_applock_vault_config(file_path)
                data_list.extend(vault_data)
                
        except Exception as e:
            logfunc(f'Error processing AppLock vault config file {file_found}: {str(e)}')
            continue
    
    # Sort by vault created time (newest first)
    data_list.sort(key=lambda x: x[0] if x[0] else '', reverse=True)
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} AppLock vault configuration entries')
    
    return data_headers, data_list, source_path

@artifact_processor
def applockPreferences(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract AppLock preferences"""
    
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
        logfunc('No AppLock preference files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing AppLock preferences file: {file_path}')
            
            if file_path.endswith('.plist'):
                pref_data = parse_applock_preferences(file_path)
                data_list.extend(pref_data)
                
        except Exception as e:
            logfunc(f'Error processing AppLock preferences file {file_found}: {str(e)}')
            continue
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} AppLock preference entries')
    
    return data_headers, data_list, source_path

@artifact_processor
def applockBookmarks(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract AppLock protected bookmarks"""
    
    data_list = []
    
    data_headers = (
        ('Last Modified', 'datetime'),
        'Bookmark Name',
        'URL',
        'Bookmark ID',
        'Internal ID',
        'Sort Order',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No AppLock database files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing AppLock bookmarks file: {file_path}')
            
            if file_path.endswith('.db'):
                bookmarks_data = parse_applock_bookmarks(file_path)
                data_list.extend(bookmarks_data)
                
        except Exception as e:
            logfunc(f'Error processing AppLock bookmarks file {file_found}: {str(e)}')
            continue
    
    # Sort by last modified time (newest first)
    data_list.sort(key=lambda x: x[0] if x[0] else '', reverse=True)
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} AppLock protected bookmarks')
    
    return data_headers, data_list, source_path