"""
All User Photos Aggregator for iLEAPP

This artifact aggregates every photo found on an iOS device from multiple sources:
- Photos.sqlite (native photo library)
- SMS/iMessage attachments 
- WhatsApp media
- Discord attachments
- Telegram media
- Signal media

Author: iLEAPP Enhanced
Version: 1.0
Date: 2025-07-26
"""

__artifacts_v2__ = {
    "allUserPhotos": {
        "name": "All User Photos",
        "description": "Comprehensive aggregation of every user photo from all sources including Photos.sqlite, messaging apps, and third-party applications",
        "author": "@iLEAPP-Enhanced",
        "version": "1.0",
        "date": "2025-07-26",
        "requirements": "none",
        "category": "Media Aggregation",
        "notes": "Aggregates photos from Photos.sqlite, SMS attachments, WhatsApp, Discord, Telegram, Signal and other messaging apps with source attribution and deduplication",
        "paths": (
            "*/PhotoData/Photos.sqlite*",                                    # Native photos library
            "*/mobile/Library/SMS/sms.db*",                                  # SMS database for attachments
            "*/mobile/Library/SMS/Attachments/**",                           # SMS attachment files
            "*/mobile/Containers/Shared/AppGroup/*/ChatStorage.sqlite*",     # WhatsApp database
            "*/mobile/Containers/Shared/AppGroup/*/Message/Media/**",        # WhatsApp media files
            "*/mobile/Containers/Data/Application/*/Documents/Database_*.sqlite*",  # Discord database
            "*/mobile/Containers/Data/Application/*/Documents/attachments/**",       # Discord attachments
            "*/mobile/Containers/Data/Application/*/Documents/*/attachment*/**",     # Telegram attachments
            "*/mobile/Containers/Data/Application/*/Library/Application Support/database*.sqlite*",  # Signal database
            "*/mobile/Containers/Data/Application/*/Library/Application Support/Attachments/**",     # Signal attachments
        ),
        "output_types": "all",
        "artifact_icon": "images"
    }
}

import os
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from packaging import version

from scripts.ilapfuncs import artifact_processor, get_file_path, get_sqlite_db_records, \
    open_sqlite_db_readonly, logfunc, iOS, convert_cocoa_core_data_ts_to_utc
from scripts.aggregation_engine import AggregationEngine


@artifact_processor
def allUserPhotos(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """
    Aggregate all user photos from multiple sources across the iOS device.
    """
    logfunc("Starting All User Photos aggregation...")
    
    data_list = []
    seen_files = set()  # For deduplication by file path
    seen_hashes = set()  # For deduplication by content hash
    
    # Process each data source
    photo_count = 0
    
    # 1. Process Photos.sqlite (native photo library)
    photos_sqlite_files = [f for f in files_found if f.endswith('Photos.sqlite') and 'PhotoData' in str(f)]
    if photos_sqlite_files:
        logfunc(f"Processing {len(photos_sqlite_files)} Photos.sqlite files...")
        photo_count += process_photos_sqlite(photos_sqlite_files, data_list, seen_files, seen_hashes, timezone_offset)
    
    # 2. Process SMS/iMessage attachments
    sms_db_files = [f for f in files_found if f.endswith('sms.db')]
    if sms_db_files:
        logfunc(f"Processing {len(sms_db_files)} SMS database files...")
        photo_count += process_sms_attachments(sms_db_files, data_list, seen_files, seen_hashes, seeker, timezone_offset)
    
    # 3. Process WhatsApp media
    whatsapp_db_files = [f for f in files_found if 'ChatStorage.sqlite' in str(f)]
    if whatsapp_db_files:
        logfunc(f"Processing {len(whatsapp_db_files)} WhatsApp databases...")
        photo_count += process_whatsapp_media(whatsapp_db_files, data_list, seen_files, seen_hashes, seeker, timezone_offset)
    
    # 4. Process Discord attachments
    discord_files = [f for f in files_found if 'Database_' in str(f) and f.endswith('.sqlite')]
    if discord_files:
        logfunc(f"Processing {len(discord_files)} Discord database files...")
        photo_count += process_discord_attachments(discord_files, data_list, seen_files, seen_hashes, seeker, timezone_offset)
    
    # 5. Process Telegram attachments
    telegram_files = [f for f in files_found if 'attachment' in str(f).lower()]
    if telegram_files:
        logfunc(f"Processing {len(telegram_files)} Telegram attachment files...")
        photo_count += process_telegram_media(telegram_files, data_list, seen_files, seen_hashes, timezone_offset)
    
    # 6. Process Signal attachments  
    signal_files = [f for f in files_found if 'database' in str(f).lower() and 'Application Support' in str(f)]
    if signal_files:
        logfunc(f"Processing {len(signal_files)} Signal database files...")
        photo_count += process_signal_attachments(signal_files, data_list, seen_files, seen_hashes, seeker, timezone_offset)
    
    # Sort by timestamp (most recent first)
    data_list.sort(key=lambda x: x[0] if x[0] else '', reverse=True)
    
    # Report to aggregation engine
    if data_list:
        AggregationEngine.report_artifact_processed("All User Photos", len(data_list))
        logfunc(f"All User Photos aggregation complete: {len(data_list)} total photos from {photo_count} unique sources")
    
    # Return standardized format
    headers = (
        ('Timestamp', 'datetime'),
        ('Date Added', 'datetime'), 
        ('Source App', 'text'),
        ('File Name', 'text'),
        ('File Path', 'text'),
        ('File Size (bytes)', 'integer'),
        ('Media Type', 'text'),
        ('Creator Bundle ID', 'text'),
        ('Editor Bundle ID', 'text'),
        ('Original File Name', 'text'),
        ('Latitude', 'text'),
        ('Longitude', 'text'),
        ('Album/Chat', 'text'),
        ('Additional Info', 'text'),
        ('File Hash (SHA256)', 'text'),
        ('Source Database', 'text')
    )
    
    return headers, data_list, files_found[0] if files_found else ''


def process_photos_sqlite(files_found, data_list, seen_files, seen_hashes, timezone_offset):
    """Process native Photos.sqlite database."""
    processed_count = 0
    
    for file_path in files_found:
        try:
            # Determine iOS version and use appropriate table/query
            ios_version = iOS.get_version()
            if ios_version and version.parse(ios_version) >= version.parse("14"):
                table_name = "ZASSET"
            else:
                table_name = "ZGENERICASSET"
            
            query = f"""
            SELECT 
                datetime({table_name}.ZDATECREATED + 978307200, 'unixepoch') as timestamp,
                datetime({table_name}.ZADDEDDATE + 978307200, 'unixepoch') as date_added,
                {table_name}.ZFILENAME as filename,
                {table_name}.ZDIRECTORY as directory,
                ZADDITIONALASSETATTRIBUTES.ZORIGINALFILESIZE as file_size,
                CASE {table_name}.ZKIND 
                    WHEN 0 THEN 'Photo'
                    WHEN 1 THEN 'Video'
                    ELSE 'Unknown'
                END as media_type,
                ZADDITIONALASSETATTRIBUTES.ZCREATORBUNDLEID as creator_bundle_id,
                ZADDITIONALASSETATTRIBUTES.ZEDITORBUNDLEID as editor_bundle_id,
                ZADDITIONALASSETATTRIBUTES.ZORIGINALFILENAME as original_filename,
                CASE WHEN {table_name}.ZLATITUDE != -180.0 THEN {table_name}.ZLATITUDE ELSE '' END as latitude,
                CASE WHEN {table_name}.ZLONGITUDE != -180.0 THEN {table_name}.ZLONGITUDE ELSE '' END as longitude,
                ZGENERICALBUM.ZTITLE as album_title,
                {table_name}.ZUUID as uuid
            FROM {table_name}
            LEFT JOIN ZADDITIONALASSETATTRIBUTES ON {table_name}.ZADDITIONALATTRIBUTES = ZADDITIONALASSETATTRIBUTES.Z_PK
            LEFT JOIN Z_26ASSETS ON {table_name}.Z_PK = Z_26ASSETS.Z_3ASSETS  
            LEFT JOIN ZGENERICALBUM ON ZGENERICALBUM.Z_PK = Z_26ASSETS.Z_26ALBUMS
            WHERE {table_name}.ZTRASHEDSTATE != 1  -- Exclude trashed photos
            ORDER BY {table_name}.ZDATECREATED DESC
            """
            
            records = get_sqlite_db_records(str(file_path), query)
            
            for record in records:
                # Build file path
                if record['directory'] and record['filename']:
                    full_path = f"{record['directory']}/{record['filename']}"
                else:
                    full_path = record['filename'] or 'Unknown'
                
                # Skip if already seen
                if full_path in seen_files:
                    continue
                    
                seen_files.add(full_path)
                
                # Determine source app
                creator = record['creator_bundle_id'] or 'com.apple.camera'
                source_app = get_friendly_app_name(creator)
                
                # Add to results
                data_list.append((
                    record['timestamp'],
                    record['date_added'], 
                    source_app,
                    record['filename'],
                    full_path,
                    record['file_size'] or 0,
                    record['media_type'],
                    record['creator_bundle_id'],
                    record['editor_bundle_id'],
                    record['original_filename'],
                    record['latitude'],
                    record['longitude'],
                    record['album_title'] or 'Camera Roll',
                    f"UUID: {record['uuid']}" if record['uuid'] else '',
                    '',  # Hash placeholder
                    str(file_path)
                ))
                
                processed_count += 1
                
        except Exception as e:
            logfunc(f"Error processing Photos.sqlite {file_path}: {str(e)}")
    
    return processed_count


def process_sms_attachments(files_found, data_list, seen_files, seen_hashes, seeker, timezone_offset):
    """Process SMS/iMessage attachments."""
    processed_count = 0
    
    for sms_db_path in files_found:
        try:
            query = """
            SELECT 
                CASE 
                    WHEN LENGTH(message.date) = 9 THEN datetime(message.date + 978307200, 'unixepoch')
                    WHEN LENGTH(message.date) = 18 THEN datetime(message.date/1000000000 + 978307200, 'unixepoch')
                    ELSE ''
                END as timestamp,
                attachment.filename as file_path,
                attachment.transfer_name as transfer_name,
                attachment.total_bytes as file_size,
                attachment.mime_type as mime_type,
                chat.chat_identifier as chat_contact,
                CASE 
                    WHEN LENGTH(attachment.created_date) = 9 THEN datetime(attachment.created_date + 978307200, 'unixepoch')
                    WHEN LENGTH(attachment.created_date) = 18 THEN datetime(attachment.created_date/1000000000 + 978307200, 'unixepoch')
                    ELSE ''
                END as attachment_created,
                message.service as service
            FROM message
            JOIN message_attachment_join maj ON message.ROWID = maj.message_id  
            JOIN attachment ON attachment.ROWID = maj.attachment_id
            LEFT JOIN chat_message_join cmj ON message.ROWID = cmj.message_id
            LEFT JOIN chat ON chat.ROWID = cmj.chat_id
            WHERE attachment.mime_type LIKE 'image/%' OR attachment.mime_type LIKE 'video/%'
            ORDER BY message.date DESC
            """
            
            records = get_sqlite_db_records(str(sms_db_path), query)
            
            for record in records:
                file_path = record['file_path']
                if not file_path or file_path in seen_files:
                    continue
                    
                seen_files.add(file_path)
                
                # Determine media type
                mime_type = record['mime_type'] or ''
                if 'image' in mime_type:
                    media_type = 'Photo'
                elif 'video' in mime_type:
                    media_type = 'Video'
                else:
                    media_type = 'Media'
                
                # Get filename
                filename = os.path.basename(file_path) if file_path else record['transfer_name']
                
                # Determine service
                service = record['service'] or 'Unknown'
                source_app = f"Messages ({service})"
                
                data_list.append((
                    record['timestamp'],
                    record['attachment_created'], 
                    source_app,
                    filename,
                    file_path,
                    record['file_size'] or 0,
                    media_type,
                    'com.apple.MobileSMS',
                    '',
                    record['transfer_name'],
                    '',  # No location data
                    '',
                    f"Chat: {record['chat_contact']}" if record['chat_contact'] else 'Messages',
                    f"Service: {service}",
                    '',  # Hash placeholder
                    str(sms_db_path)
                ))
                
                processed_count += 1
                
        except Exception as e:
            logfunc(f"Error processing SMS database {sms_db_path}: {str(e)}")
    
    return processed_count


def process_whatsapp_media(files_found, data_list, seen_files, seen_hashes, seeker, timezone_offset):
    """Process WhatsApp media files."""
    processed_count = 0
    
    for db_path in files_found:
        try:
            # Look for media files in the same app group
            app_group_path = str(db_path).split('/ChatStorage.sqlite')[0]
            media_patterns = [
                f"{app_group_path}/Message/Media/**/*",
                f"{app_group_path}/Media/**/*"
            ]
            
            # Find all media files
            media_files = []
            for pattern in media_patterns:
                found_files = seeker.search(pattern)
                if found_files:
                    media_files.extend(found_files)
            
            # Filter for image/video files
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif'}
            video_extensions = {'.mp4', '.mov', '.avi', '.m4v', '.3gp'}
            
            for media_file in media_files:
                file_path = str(media_file)
                
                if file_path in seen_files:
                    continue
                    
                file_ext = Path(file_path).suffix.lower()
                
                if file_ext in image_extensions:
                    media_type = 'Photo'
                elif file_ext in video_extensions:
                    media_type = 'Video'
                else:
                    continue  # Skip non-media files
                
                seen_files.add(file_path)
                
                # Get file stats
                try:
                    file_stat = os.stat(file_path)
                    file_size = file_stat.st_size
                    timestamp = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    file_size = 0
                    timestamp = ''
                
                filename = os.path.basename(file_path)
                
                data_list.append((
                    timestamp,
                    timestamp,  # Use same timestamp for both
                    'WhatsApp',
                    filename,
                    file_path,
                    file_size,
                    media_type,
                    'net.whatsapp.WhatsApp',
                    '',
                    filename,
                    '',  # No location data
                    '',
                    'WhatsApp Chat',
                    'WhatsApp media file',
                    '',  # Hash placeholder
                    str(db_path)
                ))
                
                processed_count += 1
                
        except Exception as e:
            logfunc(f"Error processing WhatsApp media {db_path}: {str(e)}")
    
    return processed_count


def process_discord_attachments(files_found, data_list, seen_files, seen_hashes, seeker, timezone_offset):
    """Process Discord attachments.""" 
    processed_count = 0
    
    for db_path in files_found:
        try:
            # Look for Discord attachments directory
            app_path = str(db_path).split('/Documents/')[0]
            attachment_pattern = f"{app_path}/Documents/attachments/**/*"
            
            attachment_files = seeker.search(attachment_pattern)
            if not attachment_files:
                continue
                
            # Filter for image/video files
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
            video_extensions = {'.mp4', '.mov', '.avi', '.m4v'}
            
            for attachment_file in attachment_files:
                file_path = str(attachment_file)
                
                if file_path in seen_files:
                    continue
                    
                file_ext = Path(file_path).suffix.lower()
                
                if file_ext in image_extensions:
                    media_type = 'Photo'
                elif file_ext in video_extensions:
                    media_type = 'Video'
                else:
                    continue
                
                seen_files.add(file_path)
                
                # Get file stats
                try:
                    file_stat = os.stat(file_path)
                    file_size = file_stat.st_size
                    timestamp = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    file_size = 0
                    timestamp = ''
                
                filename = os.path.basename(file_path)
                
                data_list.append((
                    timestamp,
                    timestamp,
                    'Discord',
                    filename,
                    file_path,
                    file_size,
                    media_type,
                    'com.discord.Discord',
                    '',
                    filename,
                    '',
                    '',
                    'Discord Chat',
                    'Discord attachment',
                    '',  # Hash placeholder
                    str(db_path)
                ))
                
                processed_count += 1
                
        except Exception as e:
            logfunc(f"Error processing Discord attachments {db_path}: {str(e)}")
    
    return processed_count


def process_telegram_media(files_found, data_list, seen_files, seen_hashes, timezone_offset):
    """Process Telegram media files."""
    processed_count = 0
    
    # Filter for image/video files
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    video_extensions = {'.mp4', '.mov', '.avi', '.m4v'}
    
    for file_path in files_found:
        file_path = str(file_path)
        
        if file_path in seen_files:
            continue
            
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext in image_extensions:
            media_type = 'Photo'
        elif file_ext in video_extensions:
            media_type = 'Video'
        else:
            continue
        
        seen_files.add(file_path)
        
        # Get file stats
        try:
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            timestamp = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        except:
            file_size = 0
            timestamp = ''
        
        filename = os.path.basename(file_path)
        
        data_list.append((
            timestamp,
            timestamp,
            'Telegram',
            filename,
            file_path,
            file_size,
            media_type,
            'ph.telegra.Telegraph',
            '',
            filename,
            '',
            '',
            'Telegram Chat',
            'Telegram media file',
            '',  # Hash placeholder
            'File system'
        ))
        
        processed_count += 1
    
    return processed_count


def process_signal_attachments(files_found, data_list, seen_files, seen_hashes, seeker, timezone_offset):
    """Process Signal attachments."""
    processed_count = 0
    
    for db_path in files_found:
        try:
            # Look for Signal attachments directory
            app_support_path = str(db_path).split('/database')[0]
            attachment_pattern = f"{app_support_path}/Attachments/**/*"
            
            attachment_files = seeker.search(attachment_pattern)
            if not attachment_files:
                continue
                
            # Filter for image/video files
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
            video_extensions = {'.mp4', '.mov', '.avi', '.m4v'}
            
            for attachment_file in attachment_files:
                file_path = str(attachment_file)
                
                if file_path in seen_files:
                    continue
                    
                file_ext = Path(file_path).suffix.lower()
                
                if file_ext in image_extensions:
                    media_type = 'Photo'
                elif file_ext in video_extensions:
                    media_type = 'Video'
                else:
                    continue
                
                seen_files.add(file_path)
                
                # Get file stats
                try:
                    file_stat = os.stat(file_path)
                    file_size = file_stat.st_size
                    timestamp = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    file_size = 0
                    timestamp = ''
                
                filename = os.path.basename(file_path)
                
                data_list.append((
                    timestamp,
                    timestamp,
                    'Signal',
                    filename,
                    file_path,
                    file_size,
                    media_type,
                    'org.whispersystems.signal',
                    '',
                    filename,
                    '',
                    '',
                    'Signal Chat',
                    'Signal attachment',
                    '',  # Hash placeholder
                    str(db_path)
                ))
                
                processed_count += 1
                
        except Exception as e:
            logfunc(f"Error processing Signal attachments {db_path}: {str(e)}")
    
    return processed_count


def get_friendly_app_name(bundle_id):
    """Convert bundle ID to friendly app name."""
    if not bundle_id:
        return 'Unknown'
        
    app_mapping = {
        'com.apple.camera': 'Camera',
        'com.apple.mobileslideshow': 'Photos',
        'com.apple.MobileSMS': 'Messages',
        'com.apple.facetime': 'FaceTime',
        'net.whatsapp.WhatsApp': 'WhatsApp',
        'com.discord.Discord': 'Discord',
        'ph.telegra.Telegraph': 'Telegram',
        'org.whispersystems.signal': 'Signal',
        'com.facebook.Messenger': 'Facebook Messenger',
        'com.snapchat.snapchat': 'Snapchat',
        'com.instagram.Shareext': 'Instagram',
        'com.skype.skype': 'Skype',
        'com.viber.voip': 'Viber',
        'com.zhiliaoapp.musically': 'TikTok'
    }
    
    return app_mapping.get(bundle_id, bundle_id.split('.')[-1].title())