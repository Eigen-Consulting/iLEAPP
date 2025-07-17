__artifacts_v2__ = {
    "uberAppLocations": {
        "name": "Uber App - Locations",
        "description": "Extracts location data including GPS coordinates, cities, and addresses from Uber ride-sharing app",
        "author": "@js-forensics",
        "creation_date": "2025-07-17",
        "category": "Uber",
        "paths": ('*/Documents/database.db', '*/Documents/database.db-*'),
        "output_types": "all",
        "artifact_icon": "map-pin"
    },
    "uberAppAnalytics": {
        "name": "Uber App - Analytics & Telemetry",
        "description": "Extracts device information, app usage analytics, and session data from Uber ride-sharing app",
        "author": "@js-forensics",
        "creation_date": "2025-07-17",
        "category": "Uber",
        "paths": ('*/Documents/ur_message.db', '*/Documents/ur_message.db-*'),
        "output_types": "all",
        "artifact_icon": "activity"
    },
    "uberAppRides": {
        "name": "Uber App - Rides & Feedback",
        "description": "Extracts ride intent data and user feedback from Uber ride-sharing app",
        "author": "@js-forensics",
        "creation_date": "2025-07-17",
        "category": "Uber",
        "paths": ('*/Documents/database.db', '*/Documents/database.db-*'),
        "output_types": "all",
        "artifact_icon": "car"
    }
}

import sqlite3
import json
import os
from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import artifact_processor, get_sqlite_db_records, does_table_exist_in_db, convert_unix_ts_to_utc, convert_cocoa_core_data_ts_to_utc

@artifact_processor
def uberAppLocations(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract location data from Uber app database"""
    data_list = []
    
    for file_found in files_found:
        file_found = str(file_found)
        
        if not file_found.endswith('.db') and not file_found.endswith('.db-wal') and not file_found.endswith('.db-shm'):
            continue
            
        if file_found.endswith('.db-wal') or file_found.endswith('.db-shm'):
            continue
            
        # Check if place table exists
        if not does_table_exist_in_db(file_found, 'place'):
            continue
            
        # Extract location data
        query = '''
        SELECT 
            _id as "ID",
            timestamp_ms as "Timestamp",
            latitude_v2 as "Latitude",
            longitude_v2 as "Longitude", 
            city_id as "City",
            title_segment as "Title",
            subtitle_segment as "Subtitle",
            place_result as "Place Data"
        FROM place
        WHERE latitude_v2 IS NOT NULL AND longitude_v2 IS NOT NULL
        ORDER BY _id
        '''
        
        db_records = get_sqlite_db_records(file_found, query)
        
        for record in db_records:
            # Convert timestamp from milliseconds to UTC
            timestamp_ms = record[1]
            if timestamp_ms:
                human_timestamp = convert_unix_ts_to_utc(timestamp_ms / 1000)
            else:
                human_timestamp = ''
                
            data_list.append([
                record[0],  # ID
                human_timestamp,  # Timestamp
                record[2],  # Latitude
                record[3],  # Longitude
                record[4] if record[4] else '',  # City
                record[5] if record[5] else '',  # Title
                record[6] if record[6] else '',  # Subtitle
                record[7] if record[7] else '',  # Place Data
                file_found
            ])
    
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Uber - Locations')
        report.start_artifact_report(report_folder, 'Uber - Locations')
        report.add_script()
        data_headers = ('ID', 'Timestamp', 'Latitude', 'Longitude', 'City', 'Title', 'Subtitle', 'Place Data', 'Source File')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        return data_headers, data_list, file_found
    else:
        return None, None, None

@artifact_processor
def uberAppAnalytics(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract analytics and telemetry data from Uber app message database"""
    data_list = []
    
    for file_found in files_found:
        file_found = str(file_found)
        
        if not file_found.endswith('.db') and not file_found.endswith('.db-wal') and not file_found.endswith('.db-shm'):
            continue
            
        if file_found.endswith('.db-wal') or file_found.endswith('.db-shm'):
            continue
            
        # Check if message table exists
        if not does_table_exist_in_db(file_found, 'message'):
            continue
            
        # Extract message data
        query = '''
        SELECT 
            auto_row_id as "Row ID",
            message_uuid as "Message UUID",
            createdAt as "Created At",
            content as "Content",
            message_type as "Message Type",
            status as "Status"
        FROM message
        ORDER BY createdAt DESC
        '''
        
        db_records = get_sqlite_db_records(file_found, query)
        
        for record in db_records:
            # Parse timestamp (milliseconds to UTC)
            timestamp_ms = record[2]
            if timestamp_ms:
                human_timestamp = convert_unix_ts_to_utc(timestamp_ms / 1000)
            else:
                human_timestamp = ''
                
            # Parse JSON data if available
            content = record[3]
            parsed_data = ''
            device_info = ''
            location_info = ''
            
            if content:
                try:
                    # Try to parse as JSON
                    json_data = json.loads(content)
                    
                    # Extract key forensic information
                    if 'device_model' in json_data:
                        device_info = f"Model: {json_data.get('device_model', '')}, OS: {json_data.get('os_version', '')}"
                    if 'latitude' in json_data and 'longitude' in json_data:
                        location_info = f"Lat: {json_data.get('latitude', '')}, Lon: {json_data.get('longitude', '')}"
                    
                    parsed_data = json.dumps(json_data, indent=2)[:500]  # Limit display length
                except:
                    parsed_data = str(content)[:500] if content else ''
            
            data_list.append([
                record[0] if record[0] else '',  # Row ID
                record[1] if record[1] else '',  # Message UUID
                human_timestamp,  # Timestamp
                record[4] if record[4] else '',  # Message Type
                device_info,  # Device Info
                location_info,  # Location Info
                parsed_data,  # Parsed Content
                record[5] if record[5] else '',  # Status
                file_found
            ])
    
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Uber - Analytics & Telemetry')
        report.start_artifact_report(report_folder, 'Uber - Analytics & Telemetry')
        report.add_script()
        data_headers = ('Row ID', 'Message UUID', 'Timestamp', 'Message Type', 'Device Info', 'Location Info', 'Content', 'Status', 'Source File')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        return data_headers, data_list, file_found
    else:
        return None, None, None

@artifact_processor
def uberAppRides(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract ride intent and feedback data from Uber app database"""
    data_list = []
    
    for file_found in files_found:
        file_found = str(file_found)
        
        if not file_found.endswith('.db') and not file_found.endswith('.db-wal') and not file_found.endswith('.db-shm'):
            continue
            
        if file_found.endswith('.db-wal') or file_found.endswith('.db-shm'):
            continue
        
        # Check for hits data (ride activity)
        if does_table_exist_in_db(file_found, 'hits'):
            query = '''
            SELECT 
                h._id as "Hit ID",
                h.timestamp_ms as "Timestamp",
                h.fk_place_row_id as "Place ID",
                p.title_segment as "Place Title",
                p.subtitle_segment as "Place Subtitle",
                p.latitude_v2 as "Latitude",
                p.longitude_v2 as "Longitude"
            FROM hits h
            LEFT JOIN place p ON h.fk_place_row_id = p._id
            ORDER BY h.timestamp_ms DESC
            '''
            
            db_records = get_sqlite_db_records(file_found, query)
            
            for record in db_records:
                # Convert timestamp from milliseconds
                timestamp_ms = record[1]
                if timestamp_ms:
                    human_timestamp = convert_unix_ts_to_utc(timestamp_ms / 1000)
                else:
                    human_timestamp = ''
                
                data_list.append([
                    record[0],  # Hit ID
                    human_timestamp,  # Timestamp
                    record[2] if record[2] else '',  # Place ID
                    record[3] if record[3] else '',  # Place Title
                    record[4] if record[4] else '',  # Place Subtitle
                    '',  # Value (empty for hits)
                    record[5] if record[5] else '',  # Latitude
                    record[6] if record[6] else '',  # Longitude
                    'Location Hit',  # Data Type
                    file_found
                ])
        
        # Check for accelerator data (frequent locations)
        if does_table_exist_in_db(file_found, 'accelerator'):
            query = '''
            SELECT 
                a._id as "Accelerator ID",
                a.update_timestamp_ms as "Update Timestamp",
                a.fk_place_row_id as "Place ID",
                a.title as "Title",
                a.type as "Type",
                a.score as "Score",
                p.latitude_v2 as "Latitude",
                p.longitude_v2 as "Longitude"
            FROM accelerator a
            LEFT JOIN place p ON a.fk_place_row_id = p._id
            ORDER BY a.score DESC
            '''
            
            db_records = get_sqlite_db_records(file_found, query)
            
            for record in db_records:
                # Convert timestamp from milliseconds
                timestamp_ms = record[1]
                if timestamp_ms:
                    human_timestamp = convert_unix_ts_to_utc(timestamp_ms / 1000)
                else:
                    human_timestamp = ''
                
                data_list.append([
                    record[0],  # Accelerator ID
                    human_timestamp,  # Update Timestamp
                    record[2] if record[2] else '',  # Place ID
                    record[3] if record[3] else '',  # Title
                    record[4] if record[4] else '',  # Type
                    record[5] if record[5] else '',  # Score
                    record[6] if record[6] else '',  # Latitude
                    record[7] if record[7] else '',  # Longitude
                    'Frequent Location',  # Data Type
                    file_found
                ])
    
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Uber - Rides & Feedback')
        report.start_artifact_report(report_folder, 'Uber - Rides & Feedback')
        report.add_script()
        data_headers = ('ID', 'Timestamp', 'Place ID', 'Title', 'Detail', 'Value', 'Latitude', 'Longitude', 'Data Type', 'Source File')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        return data_headers, data_list, file_found
    else:
        return None, None, None