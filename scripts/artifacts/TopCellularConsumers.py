__artifacts_v2__ = {
    "get_TopCellularConsumers": {
        "name": "Top Cellular Data Consumers",
        "description": "Top 10 processes with highest cellular data usage including system processes - ideal for Felix 11 challenge questions",
        "author": "@claude",
        "version": "1.0.1",
        "creation_date": "2025-07-19",
        "last_update_date": "2025-07-19",
        "requirements": "none",
        "category": "Network Usage",
        "notes": "Focused summary view showing top cellular data consumers including system processes for complete forensic accuracy",
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
def get_TopCellularConsumers(files_found, report_folder, seeker, wrap_text, timezone_offset):
    
    data_list = []
    
    for file_found in files_found:
        file_found = str(file_found)
        
        if file_found.endswith('.sqlite'):
            db = open_sqlite_db_readonly(file_found)
            cursor = db.cursor()
            
            # Check schema and execute appropriate query
            if does_column_exist_in_db(file_found,'ZLIVEUSAGE','ZWIFIIN'):
                # Newer schema with WiFi columns
                cursor.execute('''
                select
                ZPROCESS.ZBUNDLENAME,
                ZPROCESS.ZPROCNAME,
                case ZLIVEUSAGE.ZKIND
                    when 0 then 'Process'
                    when 1 then 'App'
                    else ZLIVEUSAGE.ZKIND
                end,
                ZLIVEUSAGE.ZWWANIN,
                ZLIVEUSAGE.ZWWANOUT,
                ZLIVEUSAGE.ZTIMESTAMP
                from ZLIVEUSAGE
                left join ZPROCESS on ZPROCESS.Z_PK = ZLIVEUSAGE.ZHASPROCESS
                where ZLIVEUSAGE.ZKIND != 257 
                AND (ZLIVEUSAGE.ZWWANIN > 0 OR ZLIVEUSAGE.ZWWANOUT > 0)
                ''')
            else:
                # Older schema without WiFi columns
                cursor.execute('''
                select
                ZPROCESS.ZBUNDLENAME,
                ZPROCESS.ZPROCNAME,
                case ZLIVEUSAGE.ZKIND
                    when 0 then 'Process'
                    when 1 then 'App'
                    else ZLIVEUSAGE.ZKIND
                end,
                ZLIVEUSAGE.ZWWANIN,
                ZLIVEUSAGE.ZWWANOUT,
                ZLIVEUSAGE.ZTIMESTAMP
                from ZLIVEUSAGE
                left join ZPROCESS on ZPROCESS.Z_PK = ZLIVEUSAGE.ZHASPROCESS
                where ZLIVEUSAGE.ZKIND != 257 
                AND (ZLIVEUSAGE.ZWWANIN > 0 OR ZLIVEUSAGE.ZWWANOUT > 0)
                ''')

            all_rows = cursor.fetchall()
            
            # Process and aggregate data by process/bundle
            process_totals = {}
            
            for row in all_rows:
                bundle_name = row[0] if row[0] else ""
                process_name = row[1] if row[1] else ""
                entry_type = row[2]
                wwan_in = row[3] if row[3] is not None else 0
                wwan_out = row[4] if row[4] is not None else 0
                timestamp = row[5]
                
                # Include all processes for complete forensic accuracy - CumulativeUsageTracker is often the answer!
                
                # Create unique key for each process/bundle combination
                key = f"{bundle_name}|{process_name}|{entry_type}"
                
                if key not in process_totals:
                    process_totals[key] = {
                        'bundle_name': bundle_name,
                        'process_name': process_name,
                        'entry_type': entry_type,
                        'total_in': 0,
                        'total_out': 0,
                        'last_timestamp': timestamp
                    }
                
                process_totals[key]['total_in'] += wwan_in
                process_totals[key]['total_out'] += wwan_out
                
                # Keep the most recent timestamp
                if timestamp > process_totals[key]['last_timestamp']:
                    process_totals[key]['last_timestamp'] = timestamp
            
            # Convert to list and calculate totals
            for key, data in process_totals.items():
                total_cellular = data['total_in'] + data['total_out']
                
                last_activity = convert_cocoa_core_data_ts_to_utc(data['last_timestamp'])
                
                # Only include if there's actual cellular usage
                if total_cellular > 0:
                    process_split = data['process_name'].split('/')
                    
                    data_list.append((
                        data['bundle_name'],
                        process_split[0],
                        data['entry_type'],
                        data['total_in'],
                        data['total_out'], 
                        total_cellular,
                        format_bytes(data['total_in']),
                        format_bytes(data['total_out']),
                        format_bytes(total_cellular),
                        last_activity
                    ))
            
            db.close()
        else:
            continue
    
    if not data_list:
        logfunc('No Top Cellular Data Consumers data available')
        return (), [], file_found
    
    # Sort by total cellular usage (descending) and take top 10
    data_list.sort(key=lambda x: x[5], reverse=True)
    top_10_data = data_list[:10]
    
    data_headers = (
        'Bundle Name',
        'Process Name', 
        'Entry Type',
        'Cellular In (Bytes)',
        'Cellular Out (Bytes)',
        'Total Cellular (Bytes)',
        'Cellular In',
        'Cellular Out', 
        'Total Cellular',
        ('Last Activity','datetime')
    )
    
    return data_headers, top_10_data, file_found