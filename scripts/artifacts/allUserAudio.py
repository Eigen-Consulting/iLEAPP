"""
All User Audio Aggregator for iLEAPP

This artifact aggregates every audio file found on an iOS device from multiple sources with
intelligent categorization by forensic relevance and functional purpose:

- User Content: Voice memos, custom ringtones, personal recordings
- Communication Audio: Voice messages, voicemail, call-related audio  
- System Audio: Notification sounds, alert tones, system personalization
- Voice Commands: Siri triggers, voice training, accessibility audio
- App Assets: Built-in app sounds, UI feedback, game audio

Features:
- Intelligent classification by forensic relevance (HIGH/MEDIUM/LOW)
- Path-based categorization with context analysis
- SHA256 hash-based deduplication
- Database context correlation
- Forensic-grade path accuracy

Author: iLEAPP Enhanced
Version: 1.0
Date: 2025-07-27
"""

__artifacts_v2__ = {
    "allUserAudio": {
        "name": "All User Audio",
        "description": "Comprehensive aggregation of every user audio file from all sources with intelligent categorization by forensic relevance and functional purpose",
        "author": "@iLEAPP-Enhanced",
        "version": "1.0", 
        "date": "2025-07-27",
        "requirements": "none",
        "category": "Media Aggregation",
        "notes": "Aggregates audio from Voice Memos, voicemail, messaging apps, system audio, and app assets with forensic relevance scoring and intelligent categorization",
        "paths": (
            # Native Voice Memos and recordings
            "*/Containers/Data/Application/*/Documents/Recordings.sqlite*",
            "*/Containers/Data/Application/*/Documents/*.sqlite*", 
            "*/Containers/Data/Application/*/Library/CoreData/*.sqlite*",
            "*/Containers/Data/Application/*/Documents/*.m4a",
            "*/Containers/Data/Application/*/Documents/*.caf",
            "*/Containers/Data/Application/*/Documents/*.mp3",
            "*/Containers/Data/Application/*/Documents/*.wav",
            
            # System voicemail and voice triggers
            "*/mobile/Library/Voicemail/voicemail.db*",
            "*/mobile/Library/Voicemail/*.amr",
            "*/mobile/Library/Voicemail/*/*.amr",
            "*/mobile/Library/VoiceTrigger/**/*.wav",
            "*/mobile/Library/VoiceTrigger/**/*.json",
            
            # SMS/iMessage audio attachments
            "*/mobile/Library/SMS/sms.db*",
            "*/mobile/Library/SMS/Attachments/**/*.m4a",
            "*/mobile/Library/SMS/Attachments/**/*.caf",
            "*/mobile/Library/SMS/Attachments/**/*.mp3",
            "*/mobile/Library/SMS/Attachments/**/*.wav",
            
            # WhatsApp audio
            "*/mobile/Containers/Shared/AppGroup/*/ChatStorage.sqlite*",
            "*/mobile/Containers/Shared/AppGroup/*/Message/Media/**/*.opus",
            "*/mobile/Containers/Shared/AppGroup/*/Message/Media/**/*.m4a", 
            "*/mobile/Containers/Shared/AppGroup/*/Message/Media/**/*.caf",
            "*/mobile/Containers/Shared/AppGroup/*/Message/Media/**/*.mp3",
            
            # Telegram audio
            "*/telegram-data/account-*/postbox/db/db_sqlite*",
            "*/telegram-data/account-*/postbox/media/**/*.ogg",
            "*/telegram-data/account-*/postbox/media/**/*.m4a",
            "*/telegram-data/account-*/postbox/media/**/*.mp3",
            
            # Signal audio
            "*/mobile/Containers/Data/Application/*/Library/Application Support/database*.sqlite*",
            "*/mobile/Containers/Data/Application/*/Library/Application Support/Attachments/**/*.m4a",
            "*/mobile/Containers/Data/Application/*/Library/Application Support/Attachments/**/*.caf",
            "*/mobile/Containers/Data/Application/*/Library/Application Support/Attachments/**/*.mp3",
            
            # Discord audio
            "*/mobile/Containers/Data/Application/*/Documents/Database_*.sqlite*",
            "*/mobile/Containers/Data/Application/*/Documents/attachments/**/*.m4a",
            "*/mobile/Containers/Data/Application/*/Documents/attachments/**/*.mp3",
            "*/mobile/Containers/Data/Application/*/Documents/attachments/**/*.wav",
            
            # System and user audio
            "*/mobile/Library/Sounds/**/*.mp3",
            "*/mobile/Library/Sounds/**/*.caf",
            "*/mobile/Library/Sounds/**/*.wav",
            "*/mobile/Library/Sounds/**/*.m4a",
            
            # App bundle audio (for completeness)
            "*/containers/Bundle/Application/*/*.app/**/*.mp3",
            "*/containers/Bundle/Application/*/*.app/**/*.caf",
            "*/containers/Bundle/Application/*/*.app/**/*.wav", 
            "*/containers/Bundle/Application/*/*.app/**/*.m4a",
            "*/containers/Bundle/Application/*/*.app/**/*.aac",
            "*/containers/Bundle/Application/*/*.app/**/*.opus",
            "*/containers/Bundle/Application/*/*.app/**/*.ogg",
            
            # Additional audio formats and locations
            "**/*.amr",
            "**/*.aac",
            "**/*.opus",
            "**/*.ogg"
        ),
        "output_types": "all",
        "artifact_icon": "volume-2"
    }
}

import os
import sqlite3
import hashlib
import fnmatch
from datetime import datetime
from pathlib import Path
from packaging import version

from scripts.ilapfuncs import artifact_processor, get_file_path, get_sqlite_db_records, \
    open_sqlite_db_readonly, logfunc, iOS, convert_cocoa_core_data_ts_to_utc, \
    convert_unix_ts_to_utc, does_table_exist_in_db
from scripts.aggregation_engine import AggregationEngine

# Comprehensive audio extension constants
SUPPORTED_AUDIO_EXTENSIONS = {
    '.m4a', '.mp3', '.wav', '.aac', '.amr', '.caf', '.ogg', '.opus'
}

# Audio Type Categories with Forensic Relevance
AUDIO_CATEGORIES = {
    "USER_CONTENT": {
        "name": "User Content",
        "forensic_relevance": "HIGH",
        "score": 3,
        "patterns": [
            "*/Library/Sounds/ringtone_*",
            "*/Containers/Data/Application/*/Documents/*.m4a",
            "*/Containers/Data/Application/*/Documents/*.caf", 
            "*/Containers/Data/Application/*/Documents/*.wav",
            "*/Containers/Data/Application/*/Documents/*.mp3",
            "*/Documents/Recordings/*"
        ]
    },
    "COMMUNICATION_AUDIO": {
        "name": "Communication Audio",
        "forensic_relevance": "HIGH", 
        "score": 3,
        "patterns": [
            "*/mobile/Library/Voicemail/*",
            "*/Message/Media/*", 
            "*/mobile/Library/SMS/Attachments/*",
            "*/postbox/media/*",
            "*/Library/Application Support/Attachments/*"
        ]
    },
    "VOICE_COMMANDS": {
        "name": "Voice Commands",
        "forensic_relevance": "MEDIUM",
        "score": 2,
        "patterns": [
            "*/Library/VoiceTrigger/*"
        ]
    },
    "SYSTEM_AUDIO": {
        "name": "System Audio", 
        "forensic_relevance": "MEDIUM",
        "score": 2,
        "patterns": [
            "*/Library/Sounds/*",
            "*/System/Library/Audio/*"
        ]
    },
    "APP_ASSETS": {
        "name": "App Assets",
        "forensic_relevance": "LOW",
        "score": 1,
        "patterns": [
            "*/containers/Bundle/Application/*/*.app/*",
            "*/*.bundle/*"
        ]
    }
}

def calculate_file_hash(file_path):
    """Calculate SHA256 hash of file for deduplication."""
    try:
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        logfunc(f"Error calculating hash for {file_path}: {str(e)}")
        return ''

def classify_audio_file(file_path, file_size):
    """
    Classify audio file based on path patterns and characteristics.
    
    Returns:
        tuple: (audio_type, functional_category, forensic_relevance, confidence)
    """
    file_path_lower = file_path.lower()
    
    # Check each category's patterns
    for category_id, category_info in AUDIO_CATEGORIES.items():
        for pattern in category_info["patterns"]:
            # Convert pattern to lowercase for case-insensitive matching
            pattern_lower = pattern.lower()
            if fnmatch.fnmatch(file_path_lower, pattern_lower):
                
                # Determine functional subcategory
                functional_category = determine_functional_category(file_path, file_size, category_id)
                
                return (
                    category_info["name"],
                    functional_category,
                    category_info["forensic_relevance"], 
                    category_info["score"]
                )
    
    # Default to Unknown if no patterns match
    return ("Unknown Audio", "Unclassified", "MEDIUM", 2)

def determine_functional_category(file_path, file_size, audio_type):
    """Determine specific functional category within audio type."""
    file_path_lower = file_path.lower()
    filename = os.path.basename(file_path_lower)
    
    if audio_type == "USER_CONTENT":
        if "ringtone" in filename:
            return "Custom Ringtone"
        elif any(x in file_path_lower for x in ["recordings", "voice memo", "voicememo"]):
            return "Voice Recording"
        else:
            return "User Audio"
            
    elif audio_type == "COMMUNICATION_AUDIO":
        if "voicemail" in file_path_lower:
            return "Voicemail"
        elif any(x in file_path_lower for x in ["whatsapp", "message", "chat"]):
            return "Voice Message"
        else:
            return "Communication"
            
    elif audio_type == "VOICE_COMMANDS":
        if "siri" in file_path_lower or "voicetrigger" in file_path_lower:
            return "Siri Voice Trigger"
        else:
            return "Voice Command"
            
    elif audio_type == "SYSTEM_AUDIO":
        if "notification" in filename or "alert" in filename:
            return "Notification Sound"
        elif "ringtone" in filename:
            return "System Ringtone"
        else:
            return "System Sound"
            
    elif audio_type == "APP_ASSETS":
        if any(x in filename for x in ["notification", "alert", "message"]):
            return "App Notification"
        elif any(x in filename for x in ["ui", "button", "click", "beep"]):
            return "UI Sound Effect"
        else:
            return "App Audio Asset"
    
    return "Other"

def get_custom_default_indicator(file_path, audio_type):
    """Determine if audio file is custom or default."""
    if audio_type in ["USER_CONTENT"]:
        return "Custom"
    elif audio_type in ["APP_ASSETS"]:
        return "Default" 
    else:
        # For system audio, try to determine based on location/name
        if "custom" in file_path.lower() or "user" in file_path.lower():
            return "Custom"
        elif "system" in file_path.lower() or "default" in file_path.lower():
            return "Default"
        else:
            return "Unknown"

@artifact_processor  
def allUserAudio(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Main processor function for all user audio aggregation."""
    
    data_list = []
    seen_hashes = set()
    processed_files = 0
    total_files = 0
    
    logfunc("Starting All User Audio aggregation with intelligent categorization...")
    
    # Count total audio files for progress tracking
    audio_files = [f for f in files_found if any(str(f).lower().endswith(ext) for ext in SUPPORTED_AUDIO_EXTENSIONS)]
    total_files = len(audio_files)
    
    logfunc(f"Found {total_files} audio files to process")
    
    # Process each audio file
    for file_path in audio_files:
        try:
            file_path_str = str(file_path)
            
            # Get file metadata
            if os.path.exists(file_path_str):
                file_stats = os.stat(file_path_str)
                file_size = file_stats.st_size
                mod_time = datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S UTC')
                
                # Calculate hash for deduplication
                file_hash = calculate_file_hash(file_path_str)
                if file_hash and file_hash in seen_hashes:
                    continue  # Skip duplicate content
                if file_hash:
                    seen_hashes.add(file_hash)
                
                # Classify the audio file (initial path-based classification)
                audio_type, functional_category, forensic_relevance, relevance_score = classify_audio_file(file_path_str, file_size)
                
                # Analyze database context for enhanced classification
                db_context = analyze_database_context(files_found, file_path_str)
                
                # Apply database context enhancements
                classification_method = "Path-based"
                database_reference = ""
                participant_info = ""
                duration = ""
                database_timestamp = mod_time  # Default to file modification time
                
                if db_context["database_reference"]:
                    database_reference = db_context["database_reference"]
                    classification_method = "Database-enhanced"
                    
                    # Use database timestamp if available
                    if db_context["database_timestamp"]:
                        database_timestamp = db_context["database_timestamp"]
                    
                    # Update participant info
                    if db_context["participant_info"]:
                        participant_info = db_context["participant_info"]
                    
                    # Update duration if available from database
                    if "duration" in db_context and db_context["duration"]:
                        duration = db_context["duration"]
                    
                    # Apply classification boost from database context
                    if db_context["classification_boost"]:
                        boost_category = db_context["classification_boost"]
                        if boost_category in AUDIO_CATEGORIES:
                            boosted_info = AUDIO_CATEGORIES[boost_category]
                            audio_type = boosted_info["name"]
                            forensic_relevance = boosted_info["forensic_relevance"]
                            relevance_score = boosted_info["score"]
                            
                            # Update functional category based on database context
                            if boost_category == "USER_CONTENT" and "Voice Memos" in database_reference:
                                functional_category = "Voice Recording"
                            elif boost_category == "COMMUNICATION_AUDIO":
                                if "voicemail" in database_reference.lower():
                                    functional_category = "Voicemail"
                                elif "whatsapp" in database_reference.lower():
                                    functional_category = "Voice Message"
                                elif "telegram" in database_reference.lower():
                                    functional_category = "Voice Message"
                                elif "signal" in database_reference.lower():
                                    functional_category = "Voice Message"
                                elif "discord" in database_reference.lower():
                                    functional_category = "Voice Message"
                                elif "sms" in database_reference.lower() or "imessage" in database_reference.lower():
                                    functional_category = "Voice Message"
                
                # Determine custom/default indicator
                custom_default = get_custom_default_indicator(file_path_str, audio_type)
                
                # Format file size
                if file_size > 1024 * 1024:
                    size_str = f"{file_size / (1024 * 1024):.2f} MB"
                elif file_size > 1024:
                    size_str = f"{file_size / 1024:.2f} KB"  
                else:
                    size_str = f"{file_size} bytes"
                
                # Extract source app/system from path
                source_app = extract_source_app(file_path_str)
                
                # Get relative path for cleaner display
                if '/mobile/' in file_path_str:
                    mobile_index = file_path_str.find('/mobile/') + len('/mobile/')
                    relative_path = file_path_str[mobile_index:]
                else:
                    relative_path = file_path_str
                
                # Add to data list with enhanced schema
                data_list.append([
                    database_timestamp,          # Timestamp (database or file timestamp)
                    audio_type,                  # Audio Type (potentially enhanced by database)
                    functional_category,         # Functional Category (potentially enhanced by database)
                    forensic_relevance,          # Forensic Relevance (potentially enhanced by database)
                    relevance_score,            # User Relevance Score (potentially enhanced by database)
                    relative_path,              # File Path
                    size_str,                   # File Size
                    duration,                   # Duration (from database if available)
                    source_app,                 # Source App/System
                    database_reference,         # Database Reference (filled by DB analysis)
                    classification_method,      # Classification Method (Path-based or Database-enhanced)
                    custom_default,             # Custom/Default Indicator
                    participant_info,           # Participant Info (from database analysis)
                    file_path_str              # Source File (full path)
                ])
                
                processed_files += 1
                
                if processed_files % 100 == 0:
                    logfunc(f"Processed {processed_files}/{total_files} audio files...")
                    
            else:
                logfunc(f"File not found: {file_path_str}")
                
        except Exception as e:
            logfunc(f"Error processing audio file {file_path}: {str(e)}")
            continue
    
    logfunc(f"All User Audio aggregation complete: {processed_files} files processed, {len(data_list)} unique files found")
    
    # Enhanced headers for forensic analysis
    data_headers = [
        ('Timestamp', 'datetime'),
        'Audio Type',
        'Functional Category', 
        'Forensic Relevance',
        'User Relevance Score',
        'File Path',
        'File Size',
        'Duration',
        'Source App/System', 
        'Database Reference',
        'Classification Method',
        'Custom/Default Indicator',
        'Participant Info',
        'Source File'
    ]
    
    if len(data_list) > 0:
        return data_headers, data_list, files_found[0] if files_found else ""
    else:
        return None, None, None

def analyze_database_context(files_found, audio_file_path):
    """
    Analyze database files to find references to audio files and extract context.
    
    Returns:
        dict: Database context information including references, timestamps, participants
    """
    context = {
        "database_reference": "",
        "database_timestamp": "",
        "participant_info": "",
        "classification_boost": None,
        "confidence_score": 1.0
    }
    
    audio_filename = os.path.basename(audio_file_path)
    audio_filename_no_ext = os.path.splitext(audio_filename)[0]
    
    # Find relevant database files
    db_files = [f for f in files_found if str(f).endswith(('.db', '.sqlite'))]
    
    for db_file in db_files:
        try:
            db_path = str(db_file)
            
            # Voice Memos database analysis
            if "recordings.sqlite" in db_path.lower():
                voice_memo_context = analyze_voice_memos_db(db_path, audio_filename)
                if voice_memo_context:
                    context.update(voice_memo_context)
                    context["classification_boost"] = "USER_CONTENT"
                    context["confidence_score"] = 0.95
                    return context
            
            # SMS database analysis  
            elif "sms.db" in db_path.lower():
                sms_context = analyze_sms_db(db_path, audio_filename)
                if sms_context:
                    context.update(sms_context)
                    context["classification_boost"] = "COMMUNICATION_AUDIO"
                    context["confidence_score"] = 0.90
                    return context
            
            # WhatsApp database analysis
            elif "chatstorage.sqlite" in db_path.lower():
                whatsapp_context = analyze_whatsapp_db(db_path, audio_filename)
                if whatsapp_context:
                    context.update(whatsapp_context)
                    context["classification_boost"] = "COMMUNICATION_AUDIO" 
                    context["confidence_score"] = 0.90
                    return context
            
            # Telegram database analysis
            elif "db_sqlite" in db_path.lower() and "telegram" in db_path.lower():
                telegram_context = analyze_telegram_db(db_path, audio_filename)
                if telegram_context:
                    context.update(telegram_context)
                    context["classification_boost"] = "COMMUNICATION_AUDIO"
                    context["confidence_score"] = 0.85
                    return context
            
            # Signal database analysis
            elif "database" in db_path.lower() and "signal" in db_path.lower():
                signal_context = analyze_signal_db(db_path, audio_filename)
                if signal_context:
                    context.update(signal_context)
                    context["classification_boost"] = "COMMUNICATION_AUDIO"
                    context["confidence_score"] = 0.85
                    return context
            
            # Discord database analysis
            elif "database_" in db_path.lower() and "discord" in db_path.lower():
                discord_context = analyze_discord_db(db_path, audio_filename)
                if discord_context:
                    context.update(discord_context)
                    context["classification_boost"] = "COMMUNICATION_AUDIO"
                    context["confidence_score"] = 0.80
                    return context
            
            # Voicemail database analysis
            elif "voicemail.db" in db_path.lower():
                voicemail_context = analyze_voicemail_db(db_path, audio_filename)
                if voicemail_context:
                    context.update(voicemail_context)
                    context["classification_boost"] = "COMMUNICATION_AUDIO"
                    context["confidence_score"] = 0.95
                    return context
                    
        except Exception as e:
            logfunc(f"Error analyzing database {db_file}: {str(e)}")
            continue
    
    return context

def analyze_voice_memos_db(db_path, audio_filename):
    """Analyze Voice Memos database for audio file references."""
    try:
        if not does_table_exist_in_db(db_path, 'ZRECORDING'):
            return None
            
        query = """
        SELECT 
            ZCREATIONDATE,
            ZTITLE,
            ZURL,
            ZDURATION
        FROM ZRECORDING 
        WHERE ZURL LIKE ?
        """
        
        records = get_sqlite_db_records(db_path, query, f"%{audio_filename}%")
        
        if records:
            record = records[0]
            creation_date = convert_cocoa_core_data_ts_to_utc(record[0]) if record[0] else ""
            title = record[1] if record[1] else ""
            duration = f"{record[3]:.2f}s" if record[3] else ""
            
            return {
                "database_reference": f"Voice Memos: {title}",
                "database_timestamp": creation_date,
                "participant_info": f"User recording: {title}",
                "duration": duration
            }
            
    except Exception as e:
        logfunc(f"Error analyzing Voice Memos DB: {str(e)}")
    
    return None

def analyze_sms_db(db_path, audio_filename):
    """Analyze SMS database for audio attachment references."""
    try:
        if not does_table_exist_in_db(db_path, 'attachment'):
            return None
            
        query = """
        SELECT 
            a.created_date,
            a.filename,
            m.text,
            h.id as phone_number
        FROM attachment a
        LEFT JOIN message m ON a.rowid = m.rowid  
        LEFT JOIN handle h ON m.handle_id = h.rowid
        WHERE a.filename LIKE ? OR a.filename LIKE ?
        """
        
        records = get_sqlite_db_records(db_path, query, f"%{audio_filename}%", f"%{os.path.splitext(audio_filename)[0]}%")
        
        if records:
            record = records[0]
            created_date = convert_cocoa_core_data_ts_to_utc(record[0]) if record[0] else ""
            phone_number = record[3] if record[3] else "Unknown"
            message_text = record[2] if record[2] else ""
            
            return {
                "database_reference": f"SMS/iMessage attachment",
                "database_timestamp": created_date,
                "participant_info": f"From/To: {phone_number}",
                "message_context": message_text[:100] if message_text else ""
            }
            
    except Exception as e:
        logfunc(f"Error analyzing SMS DB: {str(e)}")
    
    return None

def analyze_whatsapp_db(db_path, audio_filename):
    """Analyze WhatsApp database for voice message references."""
    try:
        # Check for various WhatsApp table schemas
        tables_to_check = ['ZWAMESSAGE', 'ZWAMEDIAITEM', 'message', 'media_item']
        
        for table in tables_to_check:
            if does_table_exist_in_db(db_path, table):
                if table == 'ZWAMESSAGE':
                    query = f"""
                    SELECT 
                        ZMESSAGEDATE,
                        ZFROMJID,
                        ZTOJID,
                        ZMEDIAITEM
                    FROM {table}
                    WHERE ZMEDIAITEM LIKE ?
                    """
                else:
                    # Generic query for other schemas
                    query = f"SELECT * FROM {table} WHERE filename LIKE ? OR path LIKE ?"
                    
                records = get_sqlite_db_records(db_path, query, f"%{audio_filename}%")
                
                if records and len(records) > 0:
                    record = records[0]
                    
                    if table == 'ZWAMESSAGE':
                        message_date = convert_cocoa_core_data_ts_to_utc(record[0]) if record[0] else ""
                        from_jid = record[1] if record[1] else ""
                        to_jid = record[2] if record[2] else ""
                        
                        participant = from_jid if from_jid else to_jid
                        if participant:
                            # Clean up JID format  
                            participant = participant.split('@')[0] if '@' in participant else participant
                        
                        return {
                            "database_reference": "WhatsApp voice message",
                            "database_timestamp": message_date,
                            "participant_info": f"Participant: {participant}" if participant else ""
                        }
                    else:
                        return {
                            "database_reference": "WhatsApp media",
                            "database_timestamp": "",
                            "participant_info": "WhatsApp conversation"
                        }
                        
    except Exception as e:
        logfunc(f"Error analyzing WhatsApp DB: {str(e)}")
    
    return None

def analyze_telegram_db(db_path, audio_filename):
    """Analyze Telegram database for voice message references."""
    try:
        # Telegram uses a complex binary format, but we can try to find media references
        # Look for common table patterns
        tables_to_check = ['messages', 'media', 'documents']
        
        for table in tables_to_check:
            if does_table_exist_in_db(db_path, table):
                # Try generic query - Telegram schema can vary significantly
                query = f"""
                SELECT * FROM {table} 
                WHERE (data LIKE ? OR filename LIKE ? OR path LIKE ?)
                LIMIT 5
                """
                
                try:
                    records = get_sqlite_db_records(db_path, query, f"%{audio_filename}%", f"%{audio_filename}%", f"%{audio_filename}%")
                    
                    if records and len(records) > 0:
                        return {
                            "database_reference": "Telegram voice message",
                            "database_timestamp": "",
                            "participant_info": "Telegram conversation"
                        }
                except:
                    # If specific query fails, try simplified approach
                    continue
                    
    except Exception as e:
        logfunc(f"Error analyzing Telegram DB: {str(e)}")
    
    return None

def analyze_signal_db(db_path, audio_filename):
    """Analyze Signal database for voice message references."""
    try:
        # Signal database structure
        tables_to_check = ['part', 'message', 'attachment']
        
        for table in tables_to_check:
            if does_table_exist_in_db(db_path, table):
                if table == 'part':
                    query = """
                    SELECT 
                        p.data_uri,
                        p.content_type,
                        m.date_sent,
                        m.address
                    FROM part p
                    LEFT JOIN message m ON p.mid = m._id
                    WHERE p.data_uri LIKE ? OR p.content_type LIKE 'audio%'
                    """
                else:
                    query = f"""
                    SELECT * FROM {table}
                    WHERE filename LIKE ? OR path LIKE ? OR data LIKE ?
                    LIMIT 5
                    """
                
                try:
                    if table == 'part':
                        records = get_sqlite_db_records(db_path, query, f"%{audio_filename}%")
                    else:
                        records = get_sqlite_db_records(db_path, query, f"%{audio_filename}%", f"%{audio_filename}%", f"%{audio_filename}%")
                    
                    if records and len(records) > 0:
                        record = records[0]
                        
                        if table == 'part' and len(record) >= 4:
                            date_sent = convert_unix_ts_to_utc(record[2]) if record[2] else ""
                            address = record[3] if record[3] else "Unknown"
                            
                            return {
                                "database_reference": "Signal voice message",
                                "database_timestamp": date_sent,
                                "participant_info": f"Signal contact: {address}"
                            }
                        else:
                            return {
                                "database_reference": "Signal voice message",
                                "database_timestamp": "",
                                "participant_info": "Signal conversation"
                            }
                except:
                    continue
                    
    except Exception as e:
        logfunc(f"Error analyzing Signal DB: {str(e)}")
    
    return None

def analyze_discord_db(db_path, audio_filename):
    """Analyze Discord database for voice message references."""
    try:
        # Discord database structure
        tables_to_check = ['attachments', 'messages', 'media_cache']
        
        for table in tables_to_check:
            if does_table_exist_in_db(db_path, table):
                if table == 'attachments':
                    query = """
                    SELECT 
                        a.filename,
                        a.url,
                        a.size,
                        m.timestamp,
                        m.author_id
                    FROM attachments a
                    LEFT JOIN messages m ON a.message_id = m.id
                    WHERE a.filename LIKE ?
                    """
                else:
                    query = f"""
                    SELECT * FROM {table}
                    WHERE filename LIKE ? OR url LIKE ? OR data LIKE ?
                    LIMIT 5
                    """
                
                try:
                    if table == 'attachments':
                        records = get_sqlite_db_records(db_path, query, f"%{audio_filename}%")
                    else:
                        records = get_sqlite_db_records(db_path, query, f"%{audio_filename}%", f"%{audio_filename}%", f"%{audio_filename}%")
                    
                    if records and len(records) > 0:
                        record = records[0]
                        
                        if table == 'attachments' and len(record) >= 5:
                            timestamp = record[3] if record[3] else ""
                            author_id = record[4] if record[4] else "Unknown"
                            
                            # Discord timestamps are usually in milliseconds
                            if timestamp:
                                try:
                                    timestamp_seconds = int(timestamp) / 1000
                                    discord_date = convert_unix_ts_to_utc(timestamp_seconds)
                                except:
                                    discord_date = ""
                            else:
                                discord_date = ""
                            
                            return {
                                "database_reference": "Discord voice attachment",
                                "database_timestamp": discord_date,
                                "participant_info": f"Discord user: {author_id}"
                            }
                        else:
                            return {
                                "database_reference": "Discord voice attachment",
                                "database_timestamp": "",
                                "participant_info": "Discord conversation"
                            }
                except:
                    continue
                    
    except Exception as e:
        logfunc(f"Error analyzing Discord DB: {str(e)}")
    
    return None

def analyze_voicemail_db(db_path, audio_filename):
    """Analyze voicemail database for voicemail references."""
    try:
        if not does_table_exist_in_db(db_path, 'voicemail'):
            return None
            
        # Extract potential voicemail ID from filename
        voicemail_id = os.path.splitext(audio_filename)[0]
        
        query = """
        SELECT 
            date,
            sender,
            callback_num,
            duration,
            flags
        FROM voicemail 
        WHERE ROWID = ? OR sender LIKE ? OR callback_num LIKE ?
        """
        
        records = get_sqlite_db_records(db_path, query, voicemail_id, f"%{voicemail_id}%", f"%{voicemail_id}%")
        
        if records:
            record = records[0]
            voicemail_date = convert_unix_ts_to_utc(record[0]) if record[0] else ""
            sender = record[1] if record[1] else "Unknown"
            callback_num = record[2] if record[2] else ""
            duration = f"{record[3]}s" if record[3] else ""
            
            participant_info = sender if sender != "Unknown" else callback_num
            
            return {
                "database_reference": "System Voicemail",
                "database_timestamp": voicemail_date,
                "participant_info": f"From: {participant_info}",
                "duration": duration
            }
            
    except Exception as e:
        logfunc(f"Error analyzing Voicemail DB: {str(e)}")
    
    return None

def extract_source_app(file_path):
    """Extract source app or system from file path."""
    file_path_lower = file_path.lower()
    
    # System sources
    if "/library/voicemail/" in file_path_lower:
        return "System Voicemail"
    elif "/library/voicetrigger/" in file_path_lower:
        return "Siri/Voice Triggers"
    elif "/library/sms/" in file_path_lower:
        return "Messages (SMS/iMessage)"
    elif "/library/sounds/" in file_path_lower:
        return "System Audio"
    
    # App sources
    elif "whatsapp" in file_path_lower:
        return "WhatsApp"
    elif "telegram" in file_path_lower:
        return "Telegram"
    elif "signal" in file_path_lower:
        return "Signal"
    elif "discord" in file_path_lower:
        return "Discord"
    elif "voice" in file_path_lower and "memo" in file_path_lower:
        return "Voice Memos"
    elif "/bundle/application/" in file_path_lower:
        # Try to extract app name from bundle path
        try:
            parts = file_path.split("/")
            for i, part in enumerate(parts):
                if part.endswith(".app"):
                    return part.replace(".app", "")
        except:
            pass
        return "Third-party App"
    
    return "Unknown"