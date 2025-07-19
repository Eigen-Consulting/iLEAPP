__artifacts_v2__ = {
    "get_bluetoothPaired": {
        "name": "Bluetooth Paired Devices (Combined)",
        "description": "Combined Bluetooth paired devices from both SQLite database and plist sources with deduplication",
        "author": "@js",
        "version": "0.1.0",
        "date": "2025-07-19",
        "requirements": "none",
        "category": "Bluetooth",
        "notes": "Parses both com.apple.MobileBluetooth.ledevices.paired.db and com.apple.MobileBluetooth.devices.plist, deduplicates by MAC address",
        "paths": ('**/com.apple.MobileBluetooth.ledevices.paired.db*', '**/com.apple.MobileBluetooth.devices.plist'),
        "output_types": "standard"
    }
}

import plistlib
import sqlite3
from datetime import datetime, timezone
from scripts.ilapfuncs import logfunc, artifact_processor, open_sqlite_db_readonly

@artifact_processor
def get_bluetoothPaired(files_found, report_folder, seeker, wrap_text, timezone_offset):
    # Dictionary to store unique devices by MAC address
    unique_devices = {}
    
    logfunc(f"Processing {len(files_found)} Bluetooth files...")
    
    for file_found in files_found:
        file_found = str(file_found)
        logfunc(f"Processing file: {file_found}")
        
        # Process SQLite database files
        if file_found.endswith('.db'):
            try:
                db = open_sqlite_db_readonly(file_found)
                cursor = db.cursor()
                
                cursor.execute("""
                SELECT 
                    Uuid,
                    Name,
                    NameOrigin,
                    Address,
                    ResolvedAddress,
                    LastSeenTime,
                    LastConnectionTime
                FROM 
                    PairedDevices
                """)
                
                all_rows = cursor.fetchall()
                logfunc(f"Found {len(all_rows)} devices in database")
                
                for row in all_rows:
                    uuid, name, name_origin, address, resolved_address, last_seen, last_connection = row
                    
                    # Use address as key (MAC address), fallback to resolved address if needed
                    raw_address = address if address else resolved_address
                    if raw_address:
                        # Normalize MAC address - remove "Public" or "Random" prefixes
                        mac_key = raw_address.replace("Public ", "").replace("Random ", "").strip()
                        
                        # Store or update device info
                        if mac_key not in unique_devices:
                            unique_devices[mac_key] = {}
                            logfunc(f"New device from database: {mac_key} ({name})")
                        else:
                            logfunc(f"Updating existing device from database: {mac_key} ({name})")
                        
                        unique_devices[mac_key].update({
                            'mac_address': mac_key,
                            'raw_address': raw_address,
                            'name_db': name,
                            'name_origin': name_origin,
                            'uuid': uuid,
                            'resolved_address': resolved_address,
                            'last_seen_db': last_seen,
                            'last_connection_db': last_connection,
                            'source_db': True,
                            'db_file': file_found
                        })
                
                db.close()
                
            except Exception as e:
                logfunc(f"Error processing database {file_found}: {str(e)}")
        
        # Process plist files
        elif file_found.endswith('.plist'):
            try:
                with open(file_found, 'rb') as f:
                    plist_data = plistlib.load(f)
                
                logfunc(f"Found {len(plist_data)} devices in plist")
                
                for mac_address, device_info in plist_data.items():
                    # Initialize device entry if not exists
                    if mac_address not in unique_devices:
                        unique_devices[mac_address] = {}
                        logfunc(f"New device from plist: {mac_address} ({device_info.get('Name', 'Unknown')})")
                    else:
                        logfunc(f"Updating existing device from plist: {mac_address} ({device_info.get('Name', 'Unknown')})")
                    
                    # Extract relevant information from plist
                    last_seen = device_info.get('LastSeenTime', '')
                    if last_seen:
                        try:
                            last_seen = datetime.fromtimestamp(last_seen, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                        except (ValueError, TypeError):
                            last_seen = str(last_seen)
                    
                    unique_devices[mac_address].update({
                        'mac_address': mac_address,
                        'name_plist': device_info.get('Name', ''),
                        'default_name': device_info.get('DefaultName', ''),
                        'user_name_key': device_info.get('UserNameKey', ''),
                        'device_id_product': device_info.get('DeviceIdProduct', ''),
                        'device_id_vendor': device_info.get('DeviceIdVendor', ''),
                        'last_seen_plist': last_seen,
                        'source_plist': True,
                        'plist_file': file_found
                    })
                    
            except Exception as e:
                logfunc(f"Error processing plist {file_found}: {str(e)}")
    
    # Convert unique devices to list format for reporting
    data_list = []
    
    for mac_address, device in unique_devices.items():
        # Merge names from both sources, prefer the one that's not empty
        name_db = device.get('name_db', '')
        name_plist = device.get('name_plist', '')
        default_name = device.get('default_name', '')
        
        # Choose best available name
        best_name = name_plist or name_db or default_name or 'Unknown'
        
        # Merge last seen times, prefer the one that's not empty
        last_seen_db = device.get('last_seen_db', '')
        last_seen_plist = device.get('last_seen_plist', '')
        best_last_seen = last_seen_plist or last_seen_db or ''
        
        # Determine sources
        sources = []
        if device.get('source_db'):
            sources.append('Database')
        if device.get('source_plist'):
            sources.append('Plist')
        source_info = ', '.join(sources)
        
        # Use raw address if available (shows "Public" prefix), otherwise use normalized MAC
        display_address = device.get('raw_address', mac_address)
        
        data_list.append((
            display_address,
            best_name,
            device.get('default_name', ''),
            device.get('user_name_key', ''),
            best_last_seen,
            device.get('device_id_product', ''),
            device.get('device_id_vendor', ''),
            source_info,
            device.get('uuid', '')
        ))
    
    # Sort by MAC address for consistent output
    data_list.sort(key=lambda x: x[0])
    
    # Log summary statistics
    total_unique_devices = len(unique_devices)
    logfunc(f"Total unique Bluetooth devices found: {total_unique_devices}")
    
    # Add summary row at the top
    if data_list:
        summary_row = (
            f"TOTAL UNIQUE DEVICES: {total_unique_devices}",
            "--- SUMMARY ---",
            "",
            "",
            "",
            "",
            "",
            "Combined Sources",
            ""
        )
        data_list.insert(0, summary_row)
    
    data_headers = (
        'MAC Address',
        'Device Name',
        'Default Name',
        'User Name Key',
        'Last Seen Time',
        'Product ID',
        'Vendor ID',
        'Data Source',
        'UUID'
    )
    
    # Use the last processed file as report file
    report_file = file_found if 'file_found' in locals() else ''
    
    return data_headers, data_list, report_file