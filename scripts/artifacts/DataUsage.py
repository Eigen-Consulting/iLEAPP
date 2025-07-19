__artifacts_v2__ = {
    "get_DataUsage": {
        "name": "Data Usage",
        "description": "Parses application network data usage with total cellular consumption ranking",
        "author": "@KevinPagano3",
        "version": "0.1.0",
        "creation_date": "2023-10-10",
        "last_update_date": "2025-07-19",
        "requirements": "none",
        "category": "Network Usage",
        "notes": "Enhanced with total cellular usage calculation, human-readable formatting, and sorting by highest consumers",
        "paths": ('*/wireless/Library/Databases/DataUsage.sqlite*',),
        "output_types": ["html", "tsv", "timeline", "lava"]
    }
}

import sqlite3

from scripts.ilapfuncs import artifact_processor
from scripts.ilapfuncs import logfunc, tsv, timeline, is_platform_windows, open_sqlite_db_readonly, does_column_exist_in_db, convert_cocoa_core_data_ts_to_utc

def format_bytes(bytes_value):
    """Convert bytes to human readable format"""
    if bytes_value is None:
        return "0 B"
    
    bytes_value = float(bytes_value)
    if bytes_value == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

@artifact_processor
def get_DataUsage(files_found, report_folder, seeker, wrap_text, timezone_offset):
    
    data_list = []
    
    for file_found in files_found:
        file_found = str(file_found)
        
        if file_found.endswith('.sqlite'):
            db = open_sqlite_db_readonly(file_found)
            cursor = db.cursor()
            if does_column_exist_in_db(file_found,'ZLIVEUSAGE','ZWIFIIN'):
                cursor.execute('''
                select
                ZLIVEUSAGE.ZTIMESTAMP,
                ZPROCESS.ZFIRSTTIMESTAMP,
                ZPROCESS.ZTIMESTAMP,
                ZPROCESS.ZBUNDLENAME,
                ZPROCESS.ZPROCNAME,
                case ZLIVEUSAGE.ZKIND
                    when 0 then 'Process'
                    when 1 then 'App'
                    else ZLIVEUSAGE.ZKIND
                end,
                ZLIVEUSAGE.ZWIFIIN,
                ZLIVEUSAGE.ZWIFIOUT,
                ZLIVEUSAGE.ZWWANIN,
                ZLIVEUSAGE.ZWWANOUT
                from ZLIVEUSAGE
                left join ZPROCESS on ZPROCESS.Z_PK = ZLIVEUSAGE.ZHASPROCESS
                where ZLIVEUSAGE.ZKIND != 257
                ''')

                all_rows = cursor.fetchall()
                
                for row in all_rows:
                    firstused = convert_cocoa_core_data_ts_to_utc(row[0])
                    lastused = convert_cocoa_core_data_ts_to_utc(row[1])
                    lastconnected = convert_cocoa_core_data_ts_to_utc(row[2])
                    
                    # Calculate total cellular usage
                    wwan_in = row[8] if row[8] is not None else 0
                    wwan_out = row[9] if row[9] is not None else 0
                    total_cellular = wwan_in + wwan_out
                    
                    # Skip entries with no cellular usage to reduce noise
                    if total_cellular == 0:
                        continue
                    
                    process_split = row[4].split('/')
                    
                    # Add human-readable formatting and total cellular usage
                    data_list.append((
                        lastconnected,
                        firstused,
                        lastused,
                        row[3],  # Bundle Name
                        process_split[0],  # Process Name
                        row[5],  # Entry Type
                        row[6],  # WiFi In
                        row[7],  # WiFi Out  
                        row[8],  # WWAN In
                        row[9],  # WWAN Out
                        total_cellular,  # Total Cellular Usage
                        format_bytes(row[6]),  # WiFi In (Human Readable)
                        format_bytes(row[7]),  # WiFi Out (Human Readable)
                        format_bytes(row[8]),  # WWAN In (Human Readable)
                        format_bytes(row[9]),  # WWAN Out (Human Readable) 
                        format_bytes(total_cellular)  # Total Cellular (Human Readable)
                    ))
                
                # Sort by total cellular usage (descending) to show highest consumers first
                data_list.sort(key=lambda x: x[10], reverse=True)
                
                data_headers = ((('Last Connect Timestamp','datetime'),('First Usage Timestamp','datetime'),('Last Usage Timestamp','datetime'),'Bundle Name','Process Name','Entry Type','Wifi In (Bytes)','Wifi Out (Bytes)','Mobile/WWAN In (Bytes)','Mobile/WWAN Out (Bytes)','Total Cellular (Bytes)','Wifi In','Wifi Out','Mobile/WWAN In','Mobile/WWAN Out','Total Cellular'))
                return data_headers, data_list, file_found
                 
            else:
                cursor.execute('''
                select
                ZLIVEUSAGE.ZTIMESTAMP,
                ZPROCESS.ZFIRSTTIMESTAMP,
                ZPROCESS.ZTIMESTAMP,
                ZPROCESS.ZBUNDLENAME,
                ZPROCESS.ZPROCNAME,
                case ZLIVEUSAGE.ZKIND
                    when 0 then 'Process'
                    when 1 then 'App'
                    else ZLIVEUSAGE.ZKIND
                end,
                ZLIVEUSAGE.ZWWANIN,
                ZLIVEUSAGE.ZWWANOUT
                from ZLIVEUSAGE
                left join ZPROCESS on ZPROCESS.Z_PK = ZLIVEUSAGE.ZHASPROCESS
                where ZLIVEUSAGE.ZKIND != 257
                ''')

                all_rows = cursor.fetchall()
                
                for row in all_rows:
                    firstused = convert_cocoa_core_data_ts_to_utc(row[0])
                    lastused = convert_cocoa_core_data_ts_to_utc(row[1])
                    lastconnected = convert_cocoa_core_data_ts_to_utc(row[2])
                    
                    # Calculate total cellular usage
                    wwan_in = row[6] if row[6] is not None else 0
                    wwan_out = row[7] if row[7] is not None else 0
                    total_cellular = wwan_in + wwan_out
                    
                    # Skip entries with no cellular usage to reduce noise
                    if total_cellular == 0:
                        continue
                    
                    process_split = row[4].split('/')
                    
                    # Add human-readable formatting and total cellular usage
                    data_list.append((
                        lastconnected,
                        firstused,
                        lastused,
                        row[3],  # Bundle Name
                        process_split[0],  # Process Name
                        row[5],  # Entry Type
                        row[6],  # WWAN In
                        row[7],  # WWAN Out
                        total_cellular,  # Total Cellular Usage
                        format_bytes(row[6]),  # WWAN In (Human Readable)
                        format_bytes(row[7]),  # WWAN Out (Human Readable)
                        format_bytes(total_cellular)  # Total Cellular (Human Readable)
                    ))
                    
                # Sort by total cellular usage (descending) to show highest consumers first
                data_list.sort(key=lambda x: x[8], reverse=True)
                
                data_headers = ((('Last Connect Timestamp','datetime'),('First Usage Timestamp','datetime'),('Last Usage Timestamp','datetime'),'Bundle Name','Process Name','Entry Type','Mobile/WWAN In (Bytes)','Mobile/WWAN Out (Bytes)','Total Cellular (Bytes)','Mobile/WWAN In','Mobile/WWAN Out','Total Cellular'))
                return data_headers, data_list, file_found
                    
            db.close()
            
        else:
            continue
            
    if not data_list:
        logfunc('No Network Usage (DataUsage) - App Data available')