"""
Mobile Backup Information Parser for iLEAPP

This module parses the com.apple.MobileBackup.plist file to extract
backup and restore information from iOS devices.

Target file: private/var/root/Library/Preferences/com.apple.MobileBackup.plist
"""

import plistlib
from scripts.ilapfuncs import artifact_processor, convert_plist_date_to_utc

__artifacts_v2__ = {
    "mobileBackup": {
        "name": "Mobile Backup",
        "description": "Mobile backup and restore information from com.apple.MobileBackup.plist",
        "author": "@iLEAPP",
        "version": "2.0",
        "date": "2025-07-19",
        "category": "Device Info", 
        "paths": ('*/Preferences/com.apple.MobileBackup.plist', '*/private/var/root/Library/Preferences/com.apple.MobileBackup.plist'),
        "output_types": "all",
        "artifact_icon": "archive"
    }
}

@artifact_processor
def mobileBackup(files_found, report_folder, seeker, wrap_text, timezone_offset):
    data_list = []
    
    for file_found in files_found:
        try:
            with open(file_found, 'rb') as fp:
                pl = plistlib.load(fp)
            
            if 'BackupStateInfo' in pl:
                backup_info = pl['BackupStateInfo']
                for key, val in backup_info.items():
                    if key == 'isCloud':
                        data_list.append(('Backup Source (iCloud)', str(val), file_found))
                    elif key == 'date':
                        formatted_date = convert_plist_date_to_utc(val) if val else 'N/A'
                        data_list.append(('Backup Date', formatted_date, file_found))

            if 'RestoreInfo' in pl:
                restore_info = pl['RestoreInfo']
                for key, val in restore_info.items():
                    if key == 'BackupBuildVersion':
                        data_list.append(('Backup Build Version', str(val), file_found))
                    elif key == 'DeviceBuildVersion':
                        data_list.append(('Device Build Version', str(val), file_found))
                    elif key == 'WasCloudRestore':
                        data_list.append(('Was Cloud Restore', str(val), file_found))
                    elif key == 'RestoreDate':
                        formatted_date = convert_plist_date_to_utc(val) if val else 'N/A'
                        data_list.append(('Last Restore from Backup', formatted_date, file_found))
                        
        except Exception as e:
            data_list.append(('Error', f'Failed to parse file: {str(e)}', file_found))
    
    if data_list:
        headers = ('Finding', 'Value', 'Source File')
        return headers, data_list, files_found[0]
    else:
        return None, None, None