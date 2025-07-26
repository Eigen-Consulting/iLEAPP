__artifacts_v2__ = {
    "get_obliterated": {
        "name": "Device Wiped Status",
        "description": "Detects device wipe events by parsing the .obliterated file timestamp. This file is created when iOS performs a complete device wipe/erase operation.",
        "author": "@JohnHyla",
        "version": "0.1.0",
        "date": "2025-07-19",
        "requirements": "none",
        "category": "System",
        "notes": "Enhanced for Felix 09 forensic requirements - provides high-priority device wipe detection",
        "paths": ('**/root/.obliterated'),
        "output_types": "standard",
    }
}

import datetime
from datetime import timezone
import os
from scripts.ilapfuncs import logdevinfo, artifact_processor

@artifact_processor
def get_obliterated(files_found, report_folder, seeker, wrap_text, timezone_offset):
    data_list = []
    
    for file_found in files_found:
        file_path = str(file_found)
        
        # Try to get original file info from seeker (preserves original timestamps)
        file_info = seeker.file_infos.get(file_path) if hasattr(seeker, 'file_infos') else None
        
        if file_info and file_info.modification_date:
            # Use original modification timestamp from the extraction
            utc_modified_date = datetime.datetime.fromtimestamp(file_info.modification_date, tz=timezone.utc)
            source_path = file_info.source_path if hasattr(file_info, 'source_path') else file_path
        else:
            # Fallback: try to get timestamp from current file (may be inaccurate for copied files)
            try:
                modified_time = os.path.getmtime(file_path)
                utc_modified_date = datetime.datetime.fromtimestamp(modified_time, tz=timezone.utc)
                source_path = file_path
            except (OSError, FileNotFoundError):
                # If both methods fail, still report the finding
                logdevinfo(f'<b>Device Wipe Detected: </b>Timestamp unavailable due to file access permissions')
                logdevinfo(f'<b>Obliterated File Location: </b>{file_path}')
                
                data_list.append((
                    'Device Wipe Detected',
                    'Timestamp unavailable (permissions)',
                    file_path
                ))
                continue
        
        # Log high-priority device info
        logdevinfo(f'<b>Device Wipe Detected: </b>{utc_modified_date} (UTC)')
        logdevinfo(f'<b>Obliterated File Location: </b>{source_path}')
        
        # Add data for report
        data_list.append((
            'Device Wipe Detected',
            utc_modified_date,
            source_path
        ))

    data_headers = (
        ('Finding', 'text'),
        ('Timestamp of Wipe (UTC)', 'datetime'),
        ('Source File', 'text')
    )

    return data_headers, data_list, str(files_found[0]) if files_found else ''