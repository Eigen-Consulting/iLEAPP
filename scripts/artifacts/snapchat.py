"""
Snapchat iOS App Artifact Parser
Extracts Snapchat app data including messages, conversations, media, memories, and user data
"""

import json
import os
import sqlite3
import struct
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
    "snapchatMessages": {
        "name": "Snapchat - Messages",
        "description": "Extracts Snapchat messages and conversations including text, media, and metadata",
        "author": "@js-forensics",
        "creation_date": "2025-01-17",
        "last_update_date": "2025-01-17",
        "requirements": "none",
        "category": "Snapchat",
        "notes": "Parses Snapchat arroyo.db database for messaging data",
        "paths": (
            '*/CA6618F8-E002-4DE8-91EF-2097D7407250/Documents/user_scoped/*/arroyo/arroyo.db',
            '*/CA6618F8-E002-4DE8-91EF-2097D7407250/Documents/user_scoped/*/arroyo/arroyo.db-*',
        ),
        "output_types": "all",
        "artifact_icon": "message-square"
    },
    "snapchatMemories": {
        "name": "Snapchat - Memories",
        "description": "Extracts Snapchat memories and media assets from the memories database",
        "author": "@js-forensics",
        "creation_date": "2025-01-17",
        "last_update_date": "2025-01-17",
        "requirements": "none",
        "category": "Snapchat",
        "notes": "Parses Snapchat memories asset repository database",
        "paths": (
            '*/CA6618F8-E002-4DE8-91EF-2097D7407250/Documents/user_scoped/*/databases/memories_asset_repository.sqlite',
            '*/CA6618F8-E002-4DE8-91EF-2097D7407250/Documents/user_scoped/*/databases/memories_asset_repository.sqlite-*',
        ),
        "output_types": "all",
        "artifact_icon": "image"
    },
    "snapchatUserData": {
        "name": "Snapchat - User Data",
        "description": "Extracts Snapchat user data including profile information, preferences, and configuration",
        "author": "@js-forensics",
        "creation_date": "2025-01-17",
        "last_update_date": "2025-01-17",
        "requirements": "none",
        "category": "Snapchat",
        "notes": "Parses Snapchat user configuration files and preferences",
        "paths": (
            '*/CA6618F8-E002-4DE8-91EF-2097D7407250/Documents/user.plist',
            '*/CA6618F8-E002-4DE8-91EF-2097D7407250/Documents/auth.plist',
            '*/CA6618F8-E002-4DE8-91EF-2097D7407250/Documents/groups.plist',
            '*/CA6618F8-E002-4DE8-91EF-2097D7407250/Documents/app-start-experiments.plist',
            '*/CA6618F8-E002-4DE8-91EF-2097D7407250/Library/Preferences/com.toyopagroup.picaboo.plist',
        ),
        "output_types": "all",
        "artifact_icon": "user"
    }
}

def parse_snapchat_timestamp(timestamp_ms):
    """Convert Snapchat timestamp (milliseconds since epoch) to UTC string"""
    if timestamp_ms and timestamp_ms > 0:
        return convert_unix_ts_to_utc(timestamp_ms / 1000)
    return ''

def parse_content_type(content_type):
    """Parse Snapchat content type integer to readable string"""
    content_types = {
        0: "TEXT",
        1: "IMAGE", 
        2: "VIDEO",
        3: "AUDIO",
        4: "STICKER",
        5: "LOCATION",
        6: "BITMOJI",
        7: "LIVE_LOCATION",
        8: "CAMERA_ROLL_VIDEO",
        9: "CAMERA_ROLL_PHOTO"
    }
    return content_types.get(content_type, f"UNKNOWN_{content_type}")

def parse_message_state(state_type):
    """Parse message state type to readable string"""
    states = {
        "PENDING": "Pending",
        "SENT": "Sent",
        "DELIVERED": "Delivered",
        "READ": "Read",
        "SCREENSHOT": "Screenshot",
        "REPLAYED": "Replayed",
        "FAILED": "Failed",
        "EXPIRED": "Expired"
    }
    return states.get(state_type, state_type)

def parse_snapchat_messages_db(db_path):
    """Parse Snapchat messages from arroyo.db database"""
    data_list = []
    
    try:
        if not does_table_exist_in_db(db_path, 'conversation_message'):
            return data_list
            
        query = '''
            SELECT 
                cm.client_conversation_id,
                cm.client_message_id,
                cm.server_message_id,
                cm.creation_timestamp,
                cm.read_timestamp,
                cm.content_type,
                cm.sender_id,
                cm.message_state_type,
                cm.is_saved,
                cm.is_viewed_by_user,
                cm.remote_media_count,
                cm.quoted_server_message_id,
                cm.bundle_id,
                cm.created_on_device,
                lmc.content
            FROM conversation_message cm
            LEFT JOIN local_message_content lmc ON cm.local_message_content_id = lmc.local_message_content_id
            ORDER BY cm.creation_timestamp DESC
        '''
        
        db_records = get_sqlite_db_records(db_path, query)
        
        for record in db_records:
            try:
                creation_time = parse_snapchat_timestamp(record['creation_timestamp'] if record['creation_timestamp'] else 0)
                read_time = parse_snapchat_timestamp(record['read_timestamp'] if record['read_timestamp'] else 0)
                content_type = parse_content_type(record['content_type'] if record['content_type'] else 0)
                message_state = parse_message_state(record['message_state_type'] if record['message_state_type'] else '')
                
                # Extract conversation participants info
                conversation_id = record['client_conversation_id'] if record['client_conversation_id'] else ''
                sender_id = record['sender_id'] if record['sender_id'] else ''
                
                # Media and interaction info
                media_count = record['remote_media_count'] if record['remote_media_count'] else 0
                is_saved = "Yes" if record['is_saved'] else "No"
                is_viewed = "Yes" if record['is_viewed_by_user'] else "No"
                created_on_device = "Yes" if record['created_on_device'] else "No"
                
                # Handle quoted messages
                quoted_msg = record['quoted_server_message_id'] if record['quoted_server_message_id'] else ''
                quoted_info = f"Reply to: {quoted_msg}" if quoted_msg else ""
                
                # Bundle info for grouped messages
                bundle_info = record['bundle_id'] if record['bundle_id'] else ''
                
                data_list.append((
                    creation_time,
                    read_time,
                    conversation_id,
                    sender_id,
                    content_type,
                    message_state,
                    str(media_count),
                    is_saved,
                    is_viewed,
                    created_on_device,
                    quoted_info,
                    bundle_info,
                    record['client_message_id'] if record['client_message_id'] else '',
                    record['server_message_id'] if record['server_message_id'] else '',
                    db_path
                ))
                
            except Exception as e:
                logfunc(f"Error processing message record: {str(e)}")
                continue
                
    except Exception as e:
        logfunc(f"Error processing Snapchat messages database {db_path}: {str(e)}")
    
    return data_list

def parse_snapchat_memories_db(db_path):
    """Parse Snapchat memories from memories_asset_repository.sqlite"""
    data_list = []
    
    try:
        if not does_table_exist_in_db(db_path, 'memories_asset'):
            return data_list
            
        query = '''
            SELECT 
                ma.id,
                ma.type,
                ma.download_url,
                ma.encryption_key,
                ma.encryption_iv,
                ma.upload_state
            FROM memories_asset ma
            ORDER BY ma.id DESC
        '''
        
        db_records = get_sqlite_db_records(db_path, query)
        
        for record in db_records:
            try:
                asset_id = record['id'] if record['id'] else ''
                asset_type = record['type'] if record['type'] else 0
                download_url = record['download_url'] if record['download_url'] else ''
                upload_state = record['upload_state'] if record['upload_state'] else 0
                
                # Encryption info (truncated for display)
                enc_key = record['encryption_key'] if record['encryption_key'] else ''
                enc_iv = record['encryption_iv'] if record['encryption_iv'] else ''
                encryption_info = "Encrypted" if enc_key and enc_iv else "Not encrypted"
                
                # Map asset type to readable string
                asset_type_map = {
                    0: "UNKNOWN",
                    1: "RAW_MEDIA",
                    2: "PROCESSED_MEDIA",
                    3: "STICKER",
                    4: "BITMOJI"
                }
                asset_type_str = asset_type_map.get(asset_type, f"TYPE_{asset_type}")
                
                # Map upload state
                upload_state_map = {
                    0: "NOT_UPLOADED",
                    1: "UPLOADING", 
                    2: "UPLOADED",
                    3: "FAILED"
                }
                upload_state_str = upload_state_map.get(upload_state, f"STATE_{upload_state}")
                
                data_list.append((
                    '',  # creation_time - not available in this schema
                    '',  # shared_time - not available in this schema
                    asset_id,
                    asset_type_str,
                    upload_state_str,
                    encryption_info,
                    download_url,
                    db_path
                ))
                
            except Exception as e:
                logfunc(f"Error processing memory record: {str(e)}")
                continue
                
    except Exception as e:
        logfunc(f"Error processing Snapchat memories database {db_path}: {str(e)}")
    
    return data_list

def parse_snapchat_user_data(file_path):
    """Parse Snapchat user data from plist files"""
    data_list = []
    
    try:
        import plistlib
        
        with open(file_path, 'rb') as file:
            plist_data = plistlib.load(file)
            
        file_name = os.path.basename(file_path)
        
        if file_name == 'user.plist':
            # Parse user profile data
            username = plist_data.get('username', '')
            user_id = plist_data.get('user_id', '')
            laguna_id = plist_data.get('laguna_id', '')
            
            # Client encryption info
            client_enc = plist_data.get('client_encryption', {})
            enc_identifier = client_enc.get('identifier', '') if client_enc else ''
            
            data_list.append((
                '',  # timestamp
                'User Profile',
                username,
                user_id,
                laguna_id,
                enc_identifier,
                '',  # additional_info
                file_path
            ))
            
        elif file_name == 'auth.plist':
            # Parse authentication data
            for key, value in plist_data.items():
                if key not in ['password', 'token', 'secret']:  # Skip sensitive data
                    data_list.append((
                        '',  # timestamp
                        'Authentication',
                        key,
                        str(value)[:100],  # Truncate long values
                        '',  # field4
                        '',  # field5
                        '',  # field6
                        file_path
                    ))
                    
        elif file_name == 'groups.plist':
            # Parse group data
            if isinstance(plist_data, dict):
                for group_id, group_data in plist_data.items():
                    if isinstance(group_data, dict):
                        group_name = group_data.get('name', '')
                        member_count = len(group_data.get('members', []))
                        
                        data_list.append((
                            '',  # timestamp
                            'Group',
                            group_name,
                            group_id,
                            str(member_count),
                            '',  # field5
                            '',  # field6
                            file_path
                        ))
                        
        else:
            # Generic plist parsing for other files
            if isinstance(plist_data, dict):
                for key, value in plist_data.items():
                    if len(str(value)) < 200:  # Skip very long values
                        data_list.append((
                            '',  # timestamp
                            f'{file_name} Config',
                            key,
                            str(value),
                            '',  # field4
                            '',  # field5
                            '',  # field6
                            file_path
                        ))
            
    except Exception as e:
        logfunc(f"Error parsing Snapchat user data file {file_path}: {str(e)}")
    
    return data_list

@artifact_processor
def snapchatMessages(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract Snapchat message data from arroyo.db database"""
    
    data_list = []
    
    data_headers = (
        ('Created Time', 'datetime'),
        ('Read Time', 'datetime'),
        'Conversation ID',
        'Sender ID',
        'Content Type',
        'Message State',
        'Media Count',
        'Is Saved',
        'Is Viewed',
        'Created on Device',
        'Quoted Message',
        'Bundle ID',
        'Client Message ID',
        'Server Message ID',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No Snapchat message files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing Snapchat messages file: {file_path}')
            
            if file_path.endswith('.db'):
                db_data = parse_snapchat_messages_db(file_path)
                data_list.extend(db_data)
                
        except Exception as e:
            logfunc(f'Error processing Snapchat messages file {file_found}: {str(e)}')
            continue
    
    # Sort by creation time (newest first)
    data_list.sort(key=lambda x: x[0] if x[0] else '', reverse=True)
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} Snapchat message entries')
    
    return data_headers, data_list, source_path

@artifact_processor
def snapchatMemories(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract Snapchat memories data from memories database"""
    
    data_list = []
    
    data_headers = (
        ('Created Time', 'datetime'),
        ('Shared Time', 'datetime'),
        'Asset ID',
        'Asset Type',
        'Upload State',
        'Encryption Status',
        'Download URL',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No Snapchat memories files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing Snapchat memories file: {file_path}')
            
            if file_path.endswith('.sqlite'):
                db_data = parse_snapchat_memories_db(file_path)
                data_list.extend(db_data)
                
        except Exception as e:
            logfunc(f'Error processing Snapchat memories file {file_found}: {str(e)}')
            continue
    
    # Sort by creation time (newest first)
    data_list.sort(key=lambda x: x[0] if x[0] else '', reverse=True)
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} Snapchat memories entries')
    
    return data_headers, data_list, source_path

@artifact_processor
def snapchatUserData(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract Snapchat user data from plist files"""
    
    data_list = []
    
    data_headers = (
        ('Timestamp', 'datetime'),
        'Data Type',
        'Key/Name',
        'Value/ID',
        'Additional Info 1',
        'Additional Info 2',
        'Additional Info 3',
        ('Source File', 'file')
    )
    
    if not files_found:
        logfunc('No Snapchat user data files found')
        return data_headers, data_list, ''
    
    for file_found in files_found:
        try:
            file_path = str(file_found)
            logfunc(f'Processing Snapchat user data file: {file_path}')
            
            if file_path.endswith('.plist'):
                plist_data = parse_snapchat_user_data(file_path)
                data_list.extend(plist_data)
                
        except Exception as e:
            logfunc(f'Error processing Snapchat user data file {file_found}: {str(e)}')
            continue
    
    source_path = str(files_found[0]) if files_found else ''
    
    logfunc(f'Found {len(data_list)} Snapchat user data entries')
    
    return data_headers, data_list, source_path