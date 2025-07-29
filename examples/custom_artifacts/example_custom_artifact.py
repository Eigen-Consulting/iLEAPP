"""
Example Custom Artifact for iLEAPP
==================================

This is a template/example showing how to create custom artifacts for iLEAPP.
Custom artifacts allow you to extend iLEAPP's functionality without modifying
the core codebase.

To use this custom artifact:
1. Save it to a directory (e.g., /my/custom/artifacts/)
2. Run iLEAPP with: --extra-artifacts /my/custom/artifacts/

Author: Your Name Here
Date: 2025-07-29
"""

import sys
import os
import sqlite3
import datetime

# IMPORTANT: Add the parent directory to sys.path to enable imports from iLEAPP
# This is necessary because custom artifacts run from outside the main iLEAPP directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the artifact_processor decorator and helper functions
from scripts.ilapfuncs import artifact_processor, convert_ts_human_to_timezone_offset
from scripts.artifact_report import ArtifactHtmlReport

# Define your artifact metadata using __artifacts_v2__ dictionary
# The key (e.g., "myCustomArtifact") must match your function name exactly
__artifacts_v2__ = {
    "myCustomArtifact": {
        # Display name shown in reports and GUI
        "name": "My Custom Artifact",
        
        # Brief description of what this artifact extracts
        "description": "Example custom artifact that demonstrates the structure",
        
        # Author information
        "author": "@yourhandle",
        
        # Version of your artifact
        "version": "1.0",
        
        # Date created/updated
        "date": "2025-07-29",
        
        # Any special requirements (use "none" if none)
        "requirements": "none",
        
        # Category - determines where it appears in the report sidebar
        # Common categories: "Accounts", "App Usage", "Communications", 
        # "Device Info", "Media", "Network", etc.
        "category": "Custom Category",
        
        # Additional notes about the artifact
        "notes": "This is an example showing custom artifact structure",
        
        # File paths to search for (supports wildcards)
        # Can be a single path or tuple of paths
        "paths": (
            "*/mobile/Library/YourApp/*.db",
            "*/Containers/Data/Application/*/Documents/custom.sqlite",
        ),
        
        # Output types - usually "all" unless you have specific needs
        "output_types": "all",
        
        # Feather icon name for the sidebar (see https://feathericons.com/)
        "artifact_icon": "star"
    }
}

# The artifact processor function
# MUST have the same name as the key in __artifacts_v2__
# MUST be decorated with @artifact_processor
@artifact_processor
def myCustomArtifact(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """
    Process custom artifact files and extract relevant data.
    
    Args:
        files_found: List of file paths that matched the search patterns
        report_folder: Path where HTML reports should be saved
        seeker: FileSeeker object for accessing files
        wrap_text: Boolean indicating if text should be wrapped
        timezone_offset: Timezone offset for timestamp conversion
    
    Returns:
        tuple: (headers, data_rows, source_file_path)
    """
    
    # Initialize your data list
    data = []
    
    # Process each file found
    for file_path in files_found:
        # Example: Process a SQLite database
        try:
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()
            
            # Example query - adjust for your specific artifact
            cursor.execute("""
                SELECT 
                    id,
                    timestamp,
                    event_type,
                    data
                FROM events
                ORDER BY timestamp DESC
            """)
            
            for row in cursor.fetchall():
                # Process each row
                event_id = row[0]
                timestamp = row[1]
                event_type = row[2]
                event_data = row[3]
                
                # Convert timestamps if needed
                if isinstance(timestamp, (int, float)):
                    # Assuming Unix timestamp
                    timestamp = datetime.datetime.fromtimestamp(timestamp)
                    timestamp = convert_ts_human_to_timezone_offset(timestamp, timezone_offset)
                
                # Add to data list
                data.append((
                    event_id,
                    timestamp,
                    event_type,
                    event_data,
                    file_path  # Always include source file
                ))
            
            conn.close()
            
        except Exception as e:
            # Handle errors gracefully
            data.append((
                "Error",
                "N/A",
                f"Error processing file: {str(e)}",
                "N/A",
                file_path
            ))
    
    # If no data found, you can return empty or add a message
    if not data:
        data.append((
            "No Data",
            "N/A",
            "No matching data found",
            "N/A",
            "N/A"
        ))
    
    # Define column headers for your data
    headers = ('Event ID', 'Timestamp', 'Event Type', 'Data', 'Source File')
    
    # Return the results
    # Format: (headers, data_rows, source_file_for_report_header)
    return headers, data, files_found[0] if files_found else "No files found"


# Additional helper functions can be added here if needed
def helper_function():
    """Example of a helper function for complex processing"""
    pass