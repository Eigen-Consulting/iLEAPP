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


def calculate_file_hash(file_path, algorithm='sha256'):
    """Calculate file hash for deduplication."""
    try:
        if not os.path.exists(file_path):
            return ''
        
        hash_obj = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception as e:
        logfunc(f"Error calculating hash for {file_path}: {str(e)}")
        return ''


def get_available_columns(cursor, table_name):
    """Get all available columns for a given table."""
    try:
        cursor.execute(f"PRAGMA table_info({table_name});")
        return {row[1] for row in cursor.fetchall()}
    except Exception as e:
        logfunc(f"Error getting columns for table {table_name}: {str(e)}")
        return set()


def get_available_tables(cursor):
    """Get all available tables in the database."""
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return {row[0] for row in cursor.fetchall()}
    except Exception as e:
        logfunc(f"Error getting tables: {str(e)}")
        return set()


def build_photos_source_app_query(available_columns, ios_version):
    """Build Photos.sqlite query with fallback columns for source app identification."""
    
    # Fallback hierarchy for source app identification
    source_app_column = None
    source_app_alias = 'source_app_identifier'
    
    if 'ZCREATORBUNDLEID' in available_columns:
        source_app_column = 'ZADDITIONALASSETATTRIBUTES.ZCREATORBUNDLEID'
        logfunc("Using ZCREATORBUNDLEID for source app identification")
    elif 'ZIMPORTEDBYBUNDLEIDENTIFIER' in available_columns:
        source_app_column = 'ZADDITIONALASSETATTRIBUTES.ZIMPORTEDBYBUNDLEIDENTIFIER' 
        logfunc("Using ZIMPORTEDBYBUNDLEIDENTIFIER for source app identification")
    elif 'ZIMPORTEDBYDISPLAYNAME' in available_columns:
        source_app_column = 'ZADDITIONALASSETATTRIBUTES.ZIMPORTEDBYDISPLAYNAME'
        logfunc("Using ZIMPORTEDBYDISPLAYNAME for source app identification")
    elif 'ZEDITORBUNDLEID' in available_columns:
        source_app_column = 'ZADDITIONALASSETATTRIBUTES.ZEDITORBUNDLEID'
        logfunc("Using ZEDITORBUNDLEID for source app identification")
    else:
        source_app_column = "'com.apple.camera'"  # Default fallback
        logfunc("No bundle ID columns found, using default Camera app")
    
    return source_app_column, source_app_alias


def detect_media_type_from_path(file_path):
    """Detect media type from file extension when database columns are missing."""
    if not file_path:
        return 'Unknown'
        
    file_ext = Path(file_path).suffix.lower()
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif', '.bmp', '.tiff'}
    video_extensions = {'.mp4', '.mov', '.avi', '.m4v', '.3gp', '.mkv', '.wmv', '.flv'}
    
    if file_ext in image_extensions:
        return 'Photo'
    elif file_ext in video_extensions:
        return 'Video'
    else:
        return 'Media'


def filter_whatsapp_database_files(files_found):
    """Filter WhatsApp database files to exclude WAL and SHM files."""
    filtered_files = []
    
    for file_path in files_found:
        file_str = str(file_path)
        
        # Skip WAL and SHM files
        if file_str.endswith('.sqlite-wal') or file_str.endswith('.sqlite-shm'):
            logfunc(f"Skipping WhatsApp auxiliary file: {file_str}")
            continue
            
        # Only process main .sqlite files  
        if 'ChatStorage.sqlite' in file_str and file_str.endswith('.sqlite'):
            filtered_files.append(file_path)
            
    return filtered_files


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
        # Filter out WAL and SHM files
        filtered_whatsapp_files = filter_whatsapp_database_files(whatsapp_db_files)
        logfunc(f"Processing {len(filtered_whatsapp_files)} WhatsApp databases (filtered from {len(whatsapp_db_files)} found)...")
        if filtered_whatsapp_files:
            photo_count += process_whatsapp_media(filtered_whatsapp_files, data_list, seen_files, seen_hashes, seeker, timezone_offset)
    
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
    """Process native Photos.sqlite database with robust schema detection."""
    processed_count = 0
    
    for file_path in files_found:
        try:
            # Determine iOS version and schema
            ios_version = iOS.get_version()
            logfunc(f"Processing Photos.sqlite for iOS version: {ios_version}")
            
            # Open database and get schema information
            db = open_sqlite_db_readonly(str(file_path))
            cursor = db.cursor()
            
            # Get available tables and columns
            available_tables = get_available_tables(cursor)
            logfunc(f"Available tables in Photos.sqlite: {sorted(available_tables)}")
            
            # Determine correct asset table
            if 'ZASSET' in available_tables:
                asset_table = 'ZASSET'
                logfunc("Using ZASSET table (iOS 14+)")
            elif 'ZGENERICASSET' in available_tables:
                asset_table = 'ZGENERICASSET'
                logfunc("Using ZGENERICASSET table (iOS 11-13)")
            else:
                logfunc(f"No supported asset table found in {file_path}")
                db.close()
                continue
            
            # Check if ZADDITIONALASSETATTRIBUTES table exists
            if 'ZADDITIONALASSETATTRIBUTES' not in available_tables:
                logfunc(f"ZADDITIONALASSETATTRIBUTES table missing in {file_path}")
                db.close()
                continue
                
            # Get available columns for both tables
            asset_columns = get_available_columns(cursor, asset_table)
            additional_columns = get_available_columns(cursor, 'ZADDITIONALASSETATTRIBUTES')
            
            # Build source app identification column with fallback hierarchy
            source_app_column, source_app_alias = build_photos_source_app_query(additional_columns, ios_version)
            
            # Determine album join strategy
            album_join_clause = ""
            album_select = "'' as album_title"
            
            if 'ZGENERICALBUM' in available_tables:
                # Try to find the correct album join table
                album_join_tables = [t for t in available_tables if t.startswith('Z_') and 'ASSETS' in t]
                if album_join_tables:
                    # Use the first available album join table (simplified approach)
                    album_join = album_join_tables[0]
                    # Try to determine correct column names
                    if 'Z_3ASSETS' in get_available_columns(cursor, album_join):
                        album_asset_col = 'Z_3ASSETS'
                        album_album_col = 'Z_26ALBUMS'
                    elif 'Z_30ASSETS' in get_available_columns(cursor, album_join):
                        album_asset_col = 'Z_30ASSETS'
                        album_album_col = 'Z_23ALBUMS'
                    elif 'Z_34ASSETS' in get_available_columns(cursor, album_join):
                        album_asset_col = 'Z_34ASSETS'
                        album_album_col = 'Z_26ALBUMS'
                    else:
                        album_join = None
                        
                    if album_join:
                        album_join_clause = f"""
                        LEFT JOIN {album_join} ON {asset_table}.Z_PK = {album_join}.{album_asset_col}  
                        LEFT JOIN ZGENERICALBUM ON ZGENERICALBUM.Z_PK = {album_join}.{album_album_col}
                        """
                        album_select = "ZGENERICALBUM.ZTITLE as album_title"
            
            # Build dynamic query based on available columns
            select_columns = []
            
            # Core required columns
            if 'ZDATECREATED' in asset_columns:
                select_columns.append(f"datetime({asset_table}.ZDATECREATED + 978307200, 'unixepoch') as timestamp")
            else:
                select_columns.append("'' as timestamp")
                
            if 'ZADDEDDATE' in asset_columns:
                select_columns.append(f"datetime({asset_table}.ZADDEDDATE + 978307200, 'unixepoch') as date_added")
            else:
                select_columns.append("'' as date_added")
                
            if 'ZFILENAME' in asset_columns:
                select_columns.append(f"{asset_table}.ZFILENAME as filename")
            else:
                select_columns.append("'' as filename")
                
            if 'ZDIRECTORY' in asset_columns:
                select_columns.append(f"{asset_table}.ZDIRECTORY as directory")
            else:
                select_columns.append("'' as directory")
            
            # Optional columns with fallbacks
            if 'ZORIGINALFILESIZE' in additional_columns:
                select_columns.append("ZADDITIONALASSETATTRIBUTES.ZORIGINALFILESIZE as file_size")
            else:
                select_columns.append("0 as file_size")
                
            if 'ZKIND' in asset_columns:
                select_columns.append(f"""
                CASE {asset_table}.ZKIND 
                    WHEN 0 THEN 'Photo'
                    WHEN 1 THEN 'Video'
                    ELSE 'Unknown'
                END as media_type""")
            else:
                select_columns.append("'Unknown' as media_type")
            
            # Source app identification (using our fallback hierarchy)
            select_columns.append(f"{source_app_column} as {source_app_alias}")
            
            # Additional metadata columns
            if 'ZEDITORBUNDLEID' in additional_columns:
                select_columns.append("ZADDITIONALASSETATTRIBUTES.ZEDITORBUNDLEID as editor_bundle_id")
            else:
                select_columns.append("'' as editor_bundle_id")
                
            if 'ZORIGINALFILENAME' in additional_columns:
                select_columns.append("ZADDITIONALASSETATTRIBUTES.ZORIGINALFILENAME as original_filename")
            else:
                select_columns.append("'' as original_filename")
                
            if 'ZLATITUDE' in asset_columns:
                select_columns.append(f"CASE WHEN {asset_table}.ZLATITUDE != -180.0 THEN {asset_table}.ZLATITUDE ELSE '' END as latitude")
            else:
                select_columns.append("'' as latitude")
                
            if 'ZLONGITUDE' in asset_columns:
                select_columns.append(f"CASE WHEN {asset_table}.ZLONGITUDE != -180.0 THEN {asset_table}.ZLONGITUDE ELSE '' END as longitude")
            else:
                select_columns.append("'' as longitude")
                
            select_columns.append(album_select)
            
            if 'ZUUID' in asset_columns:
                select_columns.append(f"{asset_table}.ZUUID as uuid")
            else:
                select_columns.append("'' as uuid")
                
            if 'ZSAVEDASSETTYPE' in asset_columns:
                select_columns.append(f"{asset_table}.ZSAVEDASSETTYPE as saved_asset_type")
            else:
                select_columns.append("0 as saved_asset_type")
            
            # Build complete query
            query = f"""
            SELECT 
                {', '.join(select_columns)}
            FROM {asset_table}
            LEFT JOIN ZADDITIONALASSETATTRIBUTES ON {asset_table}.ZADDITIONALATTRIBUTES = ZADDITIONALASSETATTRIBUTES.Z_PK
            {album_join_clause}
            WHERE ({asset_table}.ZTRASHEDSTATE != 1 OR {asset_table}.ZTRASHEDSTATE IS NULL)
            ORDER BY {asset_table}.ZDATECREATED DESC
            """
            
            logfunc(f"Executing Photos.sqlite query with {len(select_columns)} columns")
            cursor.execute(query)
            records = cursor.fetchall()
            
            # Convert to dictionary-like access
            column_names = [description[0] for description in cursor.description]
            
            for record_tuple in records:
                # Convert tuple to dictionary for easier access
                record = dict(zip(column_names, record_tuple))
                
                # Build database relative path for initial deduplication
                if record.get('directory') and record.get('filename'):
                    db_relative_path = f"{record['directory']}/{record['filename']}"
                else:
                    db_relative_path = record.get('filename') or 'Unknown'
                
                # Skip if already seen by database path
                if db_relative_path in seen_files:
                    continue
                    
                # Try to find actual filesystem path and calculate hash
                file_hash = ''
                actual_filesystem_path = db_relative_path  # Default to database path
                path_verified = False
                
                if record.get('filename'):
                    # Comprehensive path search including discovered patterns
                    photo_file_paths = [
                        # Standard DCIM paths
                        f"{str(file_path).replace('Photos.sqlite', '')}../DCIM/{record.get('directory', '')}/{record.get('filename')}",
                        f"{str(file_path).replace('PhotoData/Photos.sqlite', '')}Media/DCIM/{record.get('directory', '')}/{record.get('filename')}",
                        # Standard PhotoData paths
                        f"{str(file_path).replace('PhotoData/Photos.sqlite', '')}Media/{record.get('directory', '')}/{record.get('filename')}",
                        # Metadata/PhotoData paths (discovered pattern)
                        f"{str(file_path).replace('PhotoData/Photos.sqlite', '')}Media/PhotoData/Metadata/{record.get('directory', '')}/{record.get('filename')}",
                        # CPLAssets patterns
                        f"{str(file_path).replace('Photos.sqlite', '')}../{record.get('directory', '')}/{record.get('filename')}",
                        # Direct PhotoData patterns  
                        f"{str(file_path).replace('Photos.sqlite', '')}../PhotoData/{record.get('directory', '')}/{record.get('filename')}"
                    ]
                    
                    for photo_path in photo_file_paths:
                        if os.path.exists(photo_path):
                            # Calculate hash
                            file_hash = calculate_file_hash(photo_path)
                            if file_hash and file_hash in seen_hashes:
                                continue  # Skip duplicate content
                            if file_hash:
                                seen_hashes.add(file_hash)
                            
                            # Use actual filesystem path for reporting
                            # Convert to relative path from mobile directory for consistency
                            if '/mobile/' in photo_path:
                                # Extract path relative to mobile directory
                                mobile_index = photo_path.find('/mobile/') + len('/mobile/')
                                actual_filesystem_path = photo_path[mobile_index:]
                            else:
                                actual_filesystem_path = photo_path
                            path_verified = True
                            break
                
                seen_files.add(db_relative_path)
                
                # Get source app using the dynamic column (could be any of the fallback options)
                source_app_identifier = record.get(source_app_alias) or 'com.apple.camera'
                source_app = get_friendly_app_name(source_app_identifier)
                
                # Enhanced metadata based on saved asset type
                saved_type = record.get('saved_asset_type', 0)
                if saved_type == 0:
                    asset_source = "Saved from other source"
                elif saved_type == 2:
                    asset_source = "Photo Streams Data"
                elif saved_type == 3:
                    asset_source = "Made/saved with this device"
                elif saved_type == 7:
                    asset_source = "Deleted/Recovered"
                else:
                    asset_source = "Camera Roll"
                
                # Add to results
                data_list.append((
                    record.get('timestamp'),
                    record.get('date_added'), 
                    source_app,
                    record.get('filename'),
                    actual_filesystem_path,
                    record.get('file_size') or 0,
                    record.get('media_type'),
                    source_app_identifier,  # Use the actual identifier we found
                    record.get('editor_bundle_id'),
                    record.get('original_filename'),
                    str(record.get('latitude', '')),
                    str(record.get('longitude', '')),
                    record.get('album_title') or asset_source,
                    f"UUID: {record.get('uuid')}, Asset Type: {asset_source}, Path Verified: {path_verified}" if record.get('uuid') else f"Asset Type: {asset_source}, Path Verified: {path_verified}",
                    file_hash,
                    str(file_path)
                ))
                
                processed_count += 1
            
            db.close()
            logfunc(f"Processed {processed_count} photos from Photos.sqlite")
                
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
                db_file_path = record['file_path']
                if not db_file_path or db_file_path in seen_files:
                    continue
                    
                # Convert SMS database path to actual filesystem path
                if db_file_path.startswith('~/Library/SMS/'):
                    # Remove ~ and add /mobile prefix for actual filesystem path
                    actual_file_path = f"Library/SMS/{db_file_path[14:]}"  # Remove ~/Library/SMS/
                    path_verified = True
                else:
                    # Use database path as fallback
                    actual_file_path = db_file_path
                    path_verified = False
                    
                seen_files.add(db_file_path)
                
                # Determine media type
                mime_type = record['mime_type'] or ''
                if 'image' in mime_type:
                    media_type = 'Photo'
                elif 'video' in mime_type:
                    media_type = 'Video'
                else:
                    media_type = 'Media'
                
                # Get filename
                filename = os.path.basename(actual_file_path) if actual_file_path else record['transfer_name']
                
                # Determine service
                service = record['service'] or 'Unknown'
                source_app = f"Messages ({service})"
                
                data_list.append((
                    record['timestamp'],
                    record['attachment_created'], 
                    source_app,
                    filename,
                    actual_file_path,
                    record['file_size'] or 0,
                    media_type,
                    'com.apple.MobileSMS',
                    '',
                    record['transfer_name'],
                    '',  # No location data
                    '',
                    f"Chat: {record['chat_contact']}" if record['chat_contact'] else 'Messages',
                    f"Service: {service}, Path Verified: {path_verified}",
                    '',  # Hash placeholder
                    str(sms_db_path)
                ))
                
                processed_count += 1
                
        except Exception as e:
            logfunc(f"Error processing SMS database {sms_db_path}: {str(e)}")
    
    return processed_count


def process_whatsapp_media(files_found, data_list, seen_files, seen_hashes, seeker, timezone_offset):
    """Process WhatsApp media files with robust schema detection and fallback strategies."""
    processed_count = 0
    
    for db_path in files_found:
        logfunc(f"Processing WhatsApp database: {db_path}")
        
        try:
            # Open database and check schema
            db = open_sqlite_db_readonly(str(db_path))
            cursor = db.cursor()
            
            # Get available tables
            available_tables = get_available_tables(cursor)
            logfunc(f"Available WhatsApp tables: {sorted(available_tables)}")
            
            # Check if required tables exist
            has_media_table = 'ZWAMEDIAITEM' in available_tables
            has_message_table = 'ZWAMESSAGE' in available_tables
            
            if not has_media_table:
                logfunc(f"ZWAMEDIAITEM table not found in {db_path}, using file system fallback")
                db.close()
                processed_count += process_whatsapp_filesystem_fallback(db_path, data_list, seen_files, seen_hashes, seeker)
                continue
            
            # Get available columns for media table
            media_columns = get_available_columns(cursor, 'ZWAMEDIAITEM')
            logfunc(f"ZWAMEDIAITEM columns: {sorted(media_columns)}")
            
            # Build dynamic query based on available columns
            select_columns = []
            
            # Core columns
            if 'ZMEDIALOCALPATH' in media_columns:
                select_columns.append('ZWAMEDIAITEM.ZMEDIALOCALPATH as media_path')
            else:
                logfunc("ZMEDIALOCALPATH not found in ZWAMEDIAITEM")
                db.close()
                processed_count += process_whatsapp_filesystem_fallback(db_path, data_list, seen_files, seen_hashes, seeker)
                continue
                
            if 'ZFILESIZE' in media_columns:
                select_columns.append('ZWAMEDIAITEM.ZFILESIZE as file_size')
            else:
                select_columns.append('0 as file_size')
            
            # Media type handling with fallback
            has_media_type = 'ZMEDIATYPE' in media_columns
            if has_media_type:
                select_columns.append('ZWAMEDIAITEM.ZMEDIATYPE as media_type_id')
                logfunc("Using ZMEDIATYPE for media type detection")
            else:
                select_columns.append('NULL as media_type_id')
                logfunc("ZMEDIATYPE not available, will use file extension detection")
            
            # Message-related columns
            message_join = ""
            if has_message_table:
                message_columns = get_available_columns(cursor, 'ZWAMESSAGE')
                if 'ZMESSAGEDATE' in message_columns:
                    select_columns.append("datetime(ZWAMESSAGE.ZMESSAGEDATE + 978307200, 'unixepoch') as message_date")
                    message_join = "LEFT JOIN ZWAMESSAGE ON ZWAMEDIAITEM.ZMESSAGE = ZWAMESSAGE.Z_PK"
                    
                    if 'ZFROMJID' in message_columns:
                        select_columns.append('ZWAMESSAGE.ZFROMJID as from_jid')
                    else:
                        select_columns.append("'' as from_jid")
                        
                    if 'ZTOJID' in message_columns:
                        select_columns.append('ZWAMESSAGE.ZTOJID as to_jid')
                    else:
                        select_columns.append("'' as to_jid")
                else:
                    select_columns.extend(["'' as message_date", "'' as from_jid", "'' as to_jid"])
            else:
                select_columns.extend(["'' as message_date", "'' as from_jid", "'' as to_jid"])
            
            # Build and execute query
            query = f"""
            SELECT {', '.join(select_columns)}
            FROM ZWAMEDIAITEM
            {message_join}
            WHERE ZWAMEDIAITEM.ZMEDIALOCALPATH IS NOT NULL
            ORDER BY ZWAMEDIAITEM.Z_PK DESC
            """
            
            logfunc(f"Executing WhatsApp query with {len(select_columns)} columns")
            cursor.execute(query)
            records = cursor.fetchall()
            
            # Process records
            column_names = [description[0] for description in cursor.description]
            
            for record_tuple in records:
                record = dict(zip(column_names, record_tuple))
                
                media_path = record.get('media_path')
                if not media_path or media_path in seen_files:
                    continue
                
                # Determine media type
                if has_media_type and record.get('media_type_id') is not None:
                    # Use database media type
                    media_type_id = record['media_type_id']
                    if media_type_id == 1:
                        media_type = 'Photo'
                    elif media_type_id == 2:
                        media_type = 'Video'
                    elif media_type_id == 3:
                        media_type = 'Audio'
                    else:
                        media_type = detect_media_type_from_path(media_path)
                else:
                    # Use file extension detection
                    media_type = detect_media_type_from_path(media_path)
                
                # Skip non-visual media
                if media_type not in ['Photo', 'Video']:
                    continue
                
                seen_files.add(media_path)
                filename = os.path.basename(media_path)
                
                # Build chat context
                chat_context = 'WhatsApp Chat'
                from_jid = record.get('from_jid')
                to_jid = record.get('to_jid')
                if from_jid or to_jid:
                    chat_context = f"WhatsApp: {from_jid or 'Unknown'} -> {to_jid or 'Unknown'}"
                
                # Try to find actual filesystem path and calculate hash
                file_hash = ''
                app_group_path = str(db_path).split('/ChatStorage.sqlite')[0]
                actual_media_path = media_path  # Default to database path
                path_verified = False
                
                # Try multiple WhatsApp path patterns
                whatsapp_path_candidates = [
                    f"{app_group_path}/{media_path}",  # Direct database path
                    f"{app_group_path}/Message/{media_path}",  # With Message prefix (discovered pattern)
                    # Also try cache location
                    f"{app_group_path.replace('/Shared/AppGroup/', '/Data/Application/')}/Library/Caches/ChatMedia/{media_path.replace('Media/', '')}"
                ]
                
                for candidate_path in whatsapp_path_candidates:
                    if os.path.exists(candidate_path):
                        file_hash = calculate_file_hash(candidate_path)
                        if file_hash in seen_hashes:
                            continue
                        if file_hash:
                            seen_hashes.add(file_hash)
                        
                        # Use relative path from mobile directory for consistency
                        if '/mobile/' in candidate_path:
                            mobile_index = candidate_path.find('/mobile/') + len('/mobile/')
                            actual_media_path = candidate_path[mobile_index:]
                        else:
                            actual_media_path = candidate_path
                        path_verified = True
                        break
                
                # Use message date or current time as fallback
                message_date = record.get('message_date') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                data_list.append((
                    message_date,
                    message_date,
                    'WhatsApp',
                    filename,
                    actual_media_path,
                    record.get('file_size') or 0,
                    media_type,
                    'net.whatsapp.WhatsApp',
                    '',
                    filename,
                    '',  # No location data in WhatsApp media table
                    '',
                    chat_context,
                    f'WhatsApp {media_type}, Path Verified: {path_verified}',
                    file_hash,
                    str(db_path)
                ))
                
                processed_count += 1
            
            db.close()
            logfunc(f"Processed {processed_count} WhatsApp media items from database")
                
        except Exception as e:
            logfunc(f"Error processing WhatsApp database {db_path}: {str(e)}")
            # Fall back to file system discovery
            processed_count += process_whatsapp_filesystem_fallback(db_path, data_list, seen_files, seen_hashes, seeker)
    
    return processed_count


def process_whatsapp_filesystem_fallback(db_path, data_list, seen_files, seen_hashes, seeker):
    """Fallback method for WhatsApp media discovery using file system."""
    processed_count = 0
    
    try:
        logfunc(f"Using file system fallback for WhatsApp media discovery")
        
        # Get app group path
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
        
        logfunc(f"Found {len(media_files)} potential WhatsApp media files")
        
        # Process each media file
        for media_file in media_files:
            file_path = str(media_file)
            
            if file_path in seen_files:
                continue
                
            # Detect media type from extension
            media_type = detect_media_type_from_path(file_path)
            if media_type not in ['Photo', 'Video']:
                continue  # Skip non-visual media
            
            # Calculate hash for deduplication
            file_hash = calculate_file_hash(file_path)
            if file_hash in seen_hashes:
                continue
            if file_hash:
                seen_hashes.add(file_hash)
            
            seen_files.add(file_path)
            
            # Get file stats
            try:
                file_stat = os.stat(file_path)
                file_size = file_stat.st_size
                timestamp = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            except:
                file_size = 0
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            filename = os.path.basename(file_path)
            
            data_list.append((
                timestamp,
                timestamp,
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
                'WhatsApp media file (filesystem)',
                file_hash,
                str(db_path)
            ))
            
            processed_count += 1
            
        logfunc(f"Processed {processed_count} WhatsApp media files via filesystem")
        
    except Exception as e:
        logfunc(f"Error in WhatsApp filesystem fallback: {str(e)}")
    
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