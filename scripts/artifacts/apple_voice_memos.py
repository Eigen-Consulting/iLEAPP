__artifacts_v2__ = {
    "appleVoiceMemosRecordings": {
        "name": "Apple Voice Memos - Recordings",
        "description": "Extracts voice recording metadata including timestamps, durations, file paths, and transcription data",
        "author": "@js-forensics",
        "creation_date": "2025-07-17",
        "category": "Voice Memos",
        "paths": (
            '*/Containers/Data/Application/*/Documents/Recordings.sqlite*',
            '*/Containers/Data/Application/*/Documents/*.sqlite*',
            '*/Containers/Data/Application/*/Library/CoreData/*.sqlite*'
        ),
        "output_types": "all",
        "artifact_icon": "mic"
    },
    "appleVoiceMemosFolders": {
        "name": "Apple Voice Memos - Folders",
        "description": "Extracts voice memo folder organization and user-created categories",
        "author": "@js-forensics",
        "creation_date": "2025-07-17",
        "category": "Voice Memos",
        "paths": (
            '*/Containers/Data/Application/*/Documents/Recordings.sqlite*',
            '*/Containers/Data/Application/*/Documents/*.sqlite*',
            '*/Containers/Data/Application/*/Library/CoreData/*.sqlite*'
        ),
        "output_types": "all",
        "artifact_icon": "folder"
    },
    "appleVoiceMemosFiles": {
        "name": "Apple Voice Memos - Audio Files",
        "description": "Extracts voice memo audio files and their metadata",
        "author": "@js-forensics",
        "creation_date": "2025-07-17",
        "category": "Voice Memos",
        "paths": (
            '*/Containers/Data/Application/*/Documents/*.m4a',
            '*/Containers/Data/Application/*/Documents/*.caf',
            '*/Containers/Data/Application/*/Documents/*.mp3',
            '*/Containers/Data/Application/*/Documents/*.wav'
        ),
        "output_types": "all",
        "artifact_icon": "file-audio"
    }
}

import sqlite3
import os
import json
from datetime import datetime
from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import artifact_processor, get_sqlite_db_records, does_table_exist_in_db, convert_cocoa_core_data_ts_to_utc

@artifact_processor
def appleVoiceMemosRecordings(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract voice recording metadata from Apple Voice Memos app"""
    data_list = []
    
    for file_found in files_found:
        file_found = str(file_found)
        
        # Only process SQLite databases
        if not file_found.endswith('.db') and not file_found.endswith('.sqlite'):
            continue
            
        if file_found.endswith('.db-wal') or file_found.endswith('.db-shm'):
            continue
        
        # Look for Core Data tables - try different table names based on iOS version
        recording_tables = ['ZRECORDING', 'ZRECORDINGMODEL', 'RECORDING']
        found_table = None
        
        for table_name in recording_tables:
            if does_table_exist_in_db(file_found, table_name):
                found_table = table_name
                break
        
        if not found_table:
            continue
            
        # Build query based on found table structure
        if found_table == 'ZRECORDING':
            # Core Data format (iOS 8+)
            query = f'''
            SELECT 
                Z_PK as "Record ID",
                ZCREATIONDATE as "Creation Date",
                ZDURATION as "Duration",
                ZTITLE as "Title",
                ZURL as "File Path",
                ZDATE as "Date",
                ZEDITED as "Edited",
                ZSHARED as "Shared",
                ZSIZE as "File Size",
                ZTRANSCRIPT as "Transcript"
            FROM {found_table}
            ORDER BY ZCREATIONDATE DESC
            '''
        else:
            # Generic fallback query
            query = f'''
            SELECT 
                *
            FROM {found_table}
            ORDER BY rowid DESC
            '''
        
        db_records = get_sqlite_db_records(file_found, query)
        
        for record in db_records:
            if found_table == 'ZRECORDING':
                # Parse Core Data timestamp
                creation_date = record[1]
                if creation_date:
                    human_date = convert_cocoa_core_data_ts_to_utc(creation_date)
                else:
                    human_date = ''
                
                # Format duration
                duration = record[2]
                if duration:
                    duration_str = f"{duration:.2f} seconds"
                else:
                    duration_str = ''
                
                # Format file size
                file_size = record[8]
                if file_size:
                    size_str = f"{file_size} bytes"
                else:
                    size_str = ''
                
                data_list.append([
                    record[0],  # Record ID
                    human_date,  # Creation Date
                    duration_str,  # Duration
                    record[3] if record[3] else '',  # Title
                    record[4] if record[4] else '',  # File Path
                    'Yes' if record[6] else 'No',  # Edited
                    'Yes' if record[7] else 'No',  # Shared
                    size_str,  # File Size
                    record[9] if record[9] else '',  # Transcript
                    file_found
                ])
            else:
                # Generic record handling
                data_list.append([
                    record[0] if len(record) > 0 else '',
                    record[1] if len(record) > 1 else '',
                    record[2] if len(record) > 2 else '',
                    record[3] if len(record) > 3 else '',
                    record[4] if len(record) > 4 else '',
                    record[5] if len(record) > 5 else '',
                    record[6] if len(record) > 6 else '',
                    record[7] if len(record) > 7 else '',
                    record[8] if len(record) > 8 else '',
                    file_found
                ])
    
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Apple Voice Memos - Recordings')
        report.start_artifact_report(report_folder, 'Apple Voice Memos - Recordings')
        report.add_script()
        data_headers = ('Record ID', 'Creation Date', 'Duration', 'Title', 'File Path', 'Edited', 'Shared', 'File Size', 'Transcript', 'Source File')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        return data_headers, data_list, file_found
    else:
        return None, None, None

@artifact_processor
def appleVoiceMemosFolders(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract voice memo folder organization from Apple Voice Memos app"""
    data_list = []
    
    for file_found in files_found:
        file_found = str(file_found)
        
        # Only process SQLite databases
        if not file_found.endswith('.db') and not file_found.endswith('.sqlite'):
            continue
            
        if file_found.endswith('.db-wal') or file_found.endswith('.db-shm'):
            continue
        
        # Look for folder tables
        folder_tables = ['ZFOLDER', 'ZFOLDERMODEL', 'FOLDER']
        found_table = None
        
        for table_name in folder_tables:
            if does_table_exist_in_db(file_found, table_name):
                found_table = table_name
                break
        
        if not found_table:
            continue
            
        # Build query based on found table structure
        if found_table == 'ZFOLDER':
            query = f'''
            SELECT 
                Z_PK as "Folder ID",
                ZNAME as "Folder Name",
                ZCREATIONDATE as "Creation Date",
                ZMODIFICATIONDATE as "Modification Date",
                ZRANK as "Rank",
                ZTYPE as "Type"
            FROM {found_table}
            ORDER BY ZRANK
            '''
        else:
            query = f'''
            SELECT 
                *
            FROM {found_table}
            ORDER BY rowid
            '''
        
        db_records = get_sqlite_db_records(file_found, query)
        
        for record in db_records:
            if found_table == 'ZFOLDER':
                # Parse timestamps
                creation_date = record[2]
                if creation_date:
                    creation_human = convert_cocoa_core_data_ts_to_utc(creation_date)
                else:
                    creation_human = ''
                
                mod_date = record[3]
                if mod_date:
                    mod_human = convert_cocoa_core_data_ts_to_utc(mod_date)
                else:
                    mod_human = ''
                
                data_list.append([
                    record[0],  # Folder ID
                    record[1] if record[1] else '',  # Folder Name
                    creation_human,  # Creation Date
                    mod_human,  # Modification Date
                    record[4] if record[4] else '',  # Rank
                    record[5] if record[5] else '',  # Type
                    file_found
                ])
            else:
                # Generic handling
                data_list.append([
                    record[0] if len(record) > 0 else '',
                    record[1] if len(record) > 1 else '',
                    record[2] if len(record) > 2 else '',
                    record[3] if len(record) > 3 else '',
                    record[4] if len(record) > 4 else '',
                    record[5] if len(record) > 5 else '',
                    file_found
                ])
    
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Apple Voice Memos - Folders')
        report.start_artifact_report(report_folder, 'Apple Voice Memos - Folders')
        report.add_script()
        data_headers = ('Folder ID', 'Folder Name', 'Creation Date', 'Modification Date', 'Rank', 'Type', 'Source File')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        return data_headers, data_list, file_found
    else:
        return None, None, None

@artifact_processor
def appleVoiceMemosFiles(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract voice memo audio files and their metadata"""
    data_list = []
    
    for file_found in files_found:
        file_found = str(file_found)
        
        # Only process audio files
        if not any(file_found.endswith(ext) for ext in ['.m4a', '.caf', '.mp3', '.wav']):
            continue
        
        # Get file metadata
        try:
            file_stats = os.stat(file_found)
            file_size = file_stats.st_size
            mod_time = datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            access_time = datetime.fromtimestamp(file_stats.st_atime).strftime('%Y-%m-%d %H:%M:%S')
            
            # Extract filename
            filename = os.path.basename(file_found)
            
            # Get file extension
            file_ext = os.path.splitext(filename)[1].lower()
            
            # Format file size
            if file_size > 1024 * 1024:
                size_str = f"{file_size / (1024 * 1024):.2f} MB"
            elif file_size > 1024:
                size_str = f"{file_size / 1024:.2f} KB"
            else:
                size_str = f"{file_size} bytes"
            
            data_list.append([
                filename,  # Filename
                file_ext,  # File Type
                size_str,  # File Size
                mod_time,  # Modified Date
                access_time,  # Access Date
                file_found  # Full Path
            ])
            
        except Exception as e:
            # Handle file access errors
            data_list.append([
                os.path.basename(file_found),
                os.path.splitext(file_found)[1].lower(),
                'Error reading file',
                '',
                '',
                file_found
            ])
    
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Apple Voice Memos - Audio Files')
        report.start_artifact_report(report_folder, 'Apple Voice Memos - Audio Files')
        report.add_script()
        data_headers = ('Filename', 'File Type', 'File Size', 'Modified Date', 'Access Date', 'Full Path')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        return data_headers, data_list, file_found
    else:
        return None, None, None