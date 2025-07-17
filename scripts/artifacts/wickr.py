__artifacts_v2__ = {
    "wickrConfiguration": {
        "name": "Wickr - Configuration",
        "description": "Extracts Wickr app configuration, user preferences, and feature settings from plist files",
        "author": "@js-forensics",
        "creation_date": "2025-07-17",
        "category": "Wickr",
        "paths": (
            '*/Library/Preferences/com.mywickr.wickr.plist',
            '*/Library/Preferences/group.com.mywickr.wickr.plist',
            '*/Library/Preferences/com.wickr.networkExtension.plist'
        ),
        "output_types": "all",
        "artifact_icon": "settings"
    },
    "wickrNetworkConfig": {
        "name": "Wickr - Network Configuration",
        "description": "Extracts Wickr push notification and network server configuration",
        "author": "@js-forensics",
        "creation_date": "2025-07-17",
        "category": "Wickr",
        "paths": (
            '*/Documents/pushConfig.plist',
            '*/Documents/pushConfig.json',
            '*/Documents/*.json'
        ),
        "output_types": "all",
        "artifact_icon": "server"
    },
    "wickrAnalytics": {
        "name": "Wickr - Analytics & Usage",
        "description": "Extracts Wickr usage analytics, crash reports, and breadcrumbs for timeline analysis",
        "author": "@js-forensics",
        "creation_date": "2025-07-17",
        "category": "Wickr",
        "paths": (
            '*/Library/Caches/com.bugsnag.Bugsnag/breadcrumbs.json',
            '*/Library/Caches/com.bugsnag.Bugsnag/reports/*.json',
            '*/Library/Caches/com.bugsnag.Bugsnag/KSCrashReports/*.json'
        ),
        "output_types": "all",
        "artifact_icon": "activity"
    },
    "wickrContainerInfo": {
        "name": "Wickr - Container Information",
        "description": "Extracts Wickr app container metadata and installation information",
        "author": "@js-forensics",
        "creation_date": "2025-07-17",
        "category": "Wickr",
        "paths": (
            '*/.com.apple.mobile_container_manager.metadata.plist',
            '*/iTunesMetadata.plist',
            '*/Info.plist'
        ),
        "output_types": "all",
        "artifact_icon": "package"
    }
}

import os
import json
import plistlib
from datetime import datetime
from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import artifact_processor

def parse_iso_timestamp(timestamp_str):
    """Parse ISO 8601 timestamp to human readable format"""
    if not timestamp_str:
        return ''
    try:
        # Handle different ISO formats
        if timestamp_str.endswith('Z'):
            dt = datetime.fromisoformat(timestamp_str[:-1] + '+00:00')
        elif '+' in timestamp_str or timestamp_str.count('-') > 2:
            dt = datetime.fromisoformat(timestamp_str)
        else:
            return timestamp_str  # Return as-is if not ISO format
        
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return timestamp_str  # Return original if parsing fails

@artifact_processor
def wickrConfiguration(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract Wickr app configuration and preferences"""
    data_list = []
    
    for file_found in files_found:
        file_found = str(file_found)
        
        if not file_found.endswith('.plist'):
            continue
            
        try:
            with open(file_found, 'rb') as f:
                plist_data = plistlib.load(f)
            
            # Determine config type based on filename
            if 'com.mywickr.wickr.plist' in file_found:
                config_type = 'Main App Preferences'
            elif 'group.com.mywickr.wickr.plist' in file_found:
                config_type = 'App Group Preferences'
            elif 'com.wickr.networkExtension.plist' in file_found:
                config_type = 'Network Extension Preferences'
            else:
                config_type = 'Unknown Configuration'
            
            # Extract key-value pairs
            for key, value in plist_data.items():
                # Convert complex values to string representation
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, indent=2)[:500]  # Limit length
                elif isinstance(value, bytes):
                    value_str = f"<binary data: {len(value)} bytes>"
                else:
                    value_str = str(value)
                
                data_list.append([
                    config_type,
                    key,
                    value_str,
                    type(value).__name__,
                    file_found
                ])
                
        except Exception as e:
            # Handle plist parsing errors
            data_list.append([
                'Error',
                f"Failed to parse {os.path.basename(file_found)}",
                str(e),
                'Error',
                file_found
            ])
    
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Wickr - Configuration')
        report.start_artifact_report(report_folder, 'Wickr - Configuration')
        report.add_script()
        data_headers = ('Configuration Type', 'Key', 'Value', 'Data Type', 'Source File')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        return data_headers, data_list, file_found
    else:
        return None, None, None

@artifact_processor
def wickrNetworkConfig(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract Wickr network and push notification configuration"""
    data_list = []
    
    for file_found in files_found:
        file_found = str(file_found)
        
        try:
            if file_found.endswith('.plist'):
                with open(file_found, 'rb') as f:
                    config_data = plistlib.load(f)
                config_type = 'Push Configuration (plist)'
            elif file_found.endswith('.json'):
                with open(file_found, 'r') as f:
                    config_data = json.load(f)
                config_type = 'Network Configuration (JSON)'
            else:
                continue
            
            # Extract network configuration details
            def extract_config_recursive(data, prefix=''):
                if isinstance(data, dict):
                    for key, value in data.items():
                        current_key = f"{prefix}.{key}" if prefix else key
                        if isinstance(value, (dict, list)):
                            extract_config_recursive(value, current_key)
                        else:
                            # Look for network-related information
                            if any(term in key.lower() for term in ['url', 'host', 'server', 'endpoint', 'domain']):
                                data_list.append([
                                    config_type,
                                    current_key,
                                    str(value),
                                    'Network Endpoint',
                                    file_found
                                ])
                            elif any(term in key.lower() for term in ['token', 'key', 'id', 'uuid']):
                                data_list.append([
                                    config_type,
                                    current_key,
                                    str(value)[:50] + '...' if len(str(value)) > 50 else str(value),
                                    'Identifier',
                                    file_found
                                ])
                            else:
                                data_list.append([
                                    config_type,
                                    current_key,
                                    str(value),
                                    'Configuration',
                                    file_found
                                ])
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        extract_config_recursive(item, f"{prefix}[{i}]")
            
            extract_config_recursive(config_data)
            
        except Exception as e:
            data_list.append([
                'Error',
                f"Failed to parse {os.path.basename(file_found)}",
                str(e),
                'Error',
                file_found
            ])
    
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Wickr - Network Configuration')
        report.start_artifact_report(report_folder, 'Wickr - Network Configuration')
        report.add_script()
        data_headers = ('Configuration Type', 'Key', 'Value', 'Data Category', 'Source File')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        return data_headers, data_list, file_found
    else:
        return None, None, None

@artifact_processor
def wickrAnalytics(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract Wickr usage analytics and crash reports"""
    data_list = []
    
    for file_found in files_found:
        file_found = str(file_found)
        
        if not file_found.endswith('.json'):
            continue
            
        try:
            with open(file_found, 'r') as f:
                analytics_data = json.load(f)
            
            # Determine analytics type based on filename
            if 'breadcrumbs.json' in file_found:
                analytics_type = 'Breadcrumbs'
                # Extract breadcrumb entries
                if isinstance(analytics_data, list):
                    for entry in analytics_data:
                        if isinstance(entry, dict):
                            timestamp = entry.get('timestamp', '')
                            if timestamp:
                                timestamp = parse_iso_timestamp(timestamp)
                            
                            data_list.append([
                                analytics_type,
                                timestamp,
                                entry.get('name', ''),
                                entry.get('type', ''),
                                json.dumps(entry.get('metaData', {}))[:200],
                                file_found
                            ])
            elif 'reports' in file_found:
                analytics_type = 'Crash Report'
                # Extract crash report details
                timestamp = analytics_data.get('timestamp', '')
                if timestamp:
                    timestamp = parse_iso_timestamp(timestamp)
                
                data_list.append([
                    analytics_type,
                    timestamp,
                    analytics_data.get('errorClass', ''),
                    analytics_data.get('errorMessage', ''),
                    json.dumps(analytics_data.get('device', {}))[:200],
                    file_found
                ])
            elif 'KSCrashReports' in file_found:
                analytics_type = 'KS Crash Report'
                # Extract KSCrash details
                timestamp = analytics_data.get('report', {}).get('timestamp', '')
                if timestamp:
                    timestamp = parse_iso_timestamp(str(timestamp))
                
                crash_info = analytics_data.get('crash', {})
                data_list.append([
                    analytics_type,
                    timestamp,
                    crash_info.get('error', {}).get('type', ''),
                    crash_info.get('error', {}).get('reason', ''),
                    json.dumps(analytics_data.get('system', {}))[:200],
                    file_found
                ])
            else:
                # Generic JSON file
                analytics_type = 'Analytics Data'
                data_list.append([
                    analytics_type,
                    '',
                    os.path.basename(file_found),
                    'JSON Data',
                    json.dumps(analytics_data)[:200],
                    file_found
                ])
                
        except Exception as e:
            data_list.append([
                'Error',
                '',
                f"Failed to parse {os.path.basename(file_found)}",
                'Error',
                str(e),
                file_found
            ])
    
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Wickr - Analytics & Usage')
        report.start_artifact_report(report_folder, 'Wickr - Analytics & Usage')
        report.add_script()
        data_headers = ('Analytics Type', 'Timestamp', 'Event/Error', 'Category', 'Details', 'Source File')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        return data_headers, data_list, file_found
    else:
        return None, None, None

@artifact_processor
def wickrContainerInfo(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """Extract Wickr container and installation information"""
    data_list = []
    
    for file_found in files_found:
        file_found = str(file_found)
        
        if not file_found.endswith('.plist'):
            continue
            
        try:
            with open(file_found, 'rb') as f:
                plist_data = plistlib.load(f)
            
            # Determine container type based on filename
            if 'metadata.plist' in file_found:
                container_type = 'Container Metadata'
            elif 'iTunesMetadata.plist' in file_found:
                container_type = 'iTunes Metadata'
            elif 'Info.plist' in file_found:
                container_type = 'App Bundle Info'
            else:
                container_type = 'Unknown Container Info'
            
            # Extract key container information
            key_fields = [
                'MCMMetadataIdentifier', 'MCMMetadataInfo', 'MCMMetadataVersion',
                'CFBundleIdentifier', 'CFBundleVersion', 'CFBundleShortVersionString',
                'itemName', 'purchaseDate', 'softwareVersionBundleId',
                'bundleId', 'bundleVersion', 'purchaseDate'
            ]
            
            for key in key_fields:
                if key in plist_data:
                    value = plist_data[key]
                    if isinstance(value, (dict, list)):
                        value_str = json.dumps(value, indent=2)[:300]
                    elif isinstance(value, bytes):
                        value_str = f"<binary data: {len(value)} bytes>"
                    else:
                        value_str = str(value)
                    
                    data_list.append([
                        container_type,
                        key,
                        value_str,
                        file_found
                    ])
            
            # If no key fields found, extract all fields
            if not any(key in plist_data for key in key_fields):
                for key, value in plist_data.items():
                    if isinstance(value, (dict, list)):
                        value_str = json.dumps(value, indent=2)[:300]
                    elif isinstance(value, bytes):
                        value_str = f"<binary data: {len(value)} bytes>"
                    else:
                        value_str = str(value)
                    
                    data_list.append([
                        container_type,
                        key,
                        value_str,
                        file_found
                    ])
                    
        except Exception as e:
            data_list.append([
                'Error',
                f"Failed to parse {os.path.basename(file_found)}",
                str(e),
                file_found
            ])
    
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Wickr - Container Information')
        report.start_artifact_report(report_folder, 'Wickr - Container Information')
        report.add_script()
        data_headers = ('Container Type', 'Key', 'Value', 'Source File')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        return data_headers, data_list, file_found
    else:
        return None, None, None