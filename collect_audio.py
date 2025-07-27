#!/usr/bin/env python3
"""
Audio Collection Script for iLEAPP All User Audio Output

This script reads the TSV output from the All User Audio artifact and 
organizes audio files into forensically relevant categories:

- User_Content/: Voice memos, custom ringtones, personal recordings
- Communication_Audio/: Voice messages, voicemail, call-related audio  
- System_Audio/: Notification sounds, alert tones, system audio
- Voice_Commands/: Siri triggers, voice training, accessibility audio
- App_Assets/: Built-in app sounds, UI feedback, game audio

Usage:
    python3 collect_audio.py <tsv_file> <output_directory>
"""

import os
import sys
import csv
import shutil
from pathlib import Path
from datetime import datetime

def create_category_folders(output_dir):
    """Create organized folder structure for audio categories."""
    categories = [
        "User_Content",
        "Communication_Audio", 
        "System_Audio",
        "Voice_Commands",
        "App_Assets",
        "Unknown_Audio"
    ]
    
    for category in categories:
        category_path = os.path.join(output_dir, category)
        os.makedirs(category_path, exist_ok=True)
        
    return categories

def sanitize_filename(filename):
    """Sanitize filename for safe filesystem usage."""
    # Remove or replace problematic characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def copy_audio_file(source_path, dest_dir, audio_type, functional_category, timestamp, source_app):
    """Copy audio file to categorized folder with descriptive name."""
    
    if not os.path.exists(source_path):
        return False, f"Source file not found: {source_path}"
    
    # Extract original filename and extension
    original_filename = os.path.basename(source_path)
    name, ext = os.path.splitext(original_filename)
    
    # Create descriptive filename with timestamp and source
    if timestamp and timestamp != "":
        try:
            # Try to parse timestamp and format it
            if ":" in timestamp:
                ts_clean = timestamp.split()[0].replace("-", "_")
            else:
                ts_clean = "unknown_date"
        except:
            ts_clean = "unknown_date"
    else:
        ts_clean = "unknown_date"
    
    # Sanitize components
    source_app_clean = sanitize_filename(source_app.replace(" ", "_"))
    functional_category_clean = sanitize_filename(functional_category.replace(" ", "_"))
    
    # Create new filename: timestamp_source_category_original
    new_filename = f"{ts_clean}_{source_app_clean}_{functional_category_clean}_{original_filename}"
    new_filename = sanitize_filename(new_filename)
    
    dest_path = os.path.join(dest_dir, new_filename)
    
    # Handle duplicate names
    counter = 1
    base_dest_path = dest_path
    while os.path.exists(dest_path):
        name_part, ext_part = os.path.splitext(base_dest_path)
        dest_path = f"{name_part}_({counter}){ext_part}"
        counter += 1
    
    try:
        shutil.copy2(source_path, dest_path)
        return True, dest_path
    except Exception as e:
        return False, str(e)

def map_audio_type_to_folder(audio_type):
    """Map audio type to folder name."""
    mapping = {
        "User Content": "User_Content",
        "Communication Audio": "Communication_Audio",
        "System Audio": "System_Audio", 
        "Voice Commands": "Voice_Commands",
        "App Assets": "App_Assets",
        "Unknown Audio": "Unknown_Audio"
    }
    return mapping.get(audio_type, "Unknown_Audio")

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 collect_audio.py <tsv_file> <output_directory>")
        print("\nExample:")
        print("python3 collect_audio.py test_audio_output/iLEAPP_Reports_*/All_User_Audio.tsv collected_audio")
        sys.exit(1)
    
    tsv_file = sys.argv[1]
    output_dir = sys.argv[2]
    
    if not os.path.exists(tsv_file):
        print(f"Error: TSV file not found: {tsv_file}")
        sys.exit(1)
    
    # Create output directory and category folders
    os.makedirs(output_dir, exist_ok=True)
    categories = create_category_folders(output_dir)
    
    # Statistics tracking
    stats = {category: {"attempted": 0, "successful": 0, "failed": 0} for category in categories}
    total_attempted = 0
    total_successful = 0
    errors = []
    
    print(f"🎵 Audio Collection Script")
    print(f"Reading TSV: {tsv_file}")
    print(f"Output directory: {output_dir}")
    print(f"Created category folders: {', '.join(categories)}")
    print()
    
    # Read TSV and process audio files
    try:
        with open(tsv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            
            for row in reader:
                # Extract relevant columns
                audio_type = row.get('Audio Type', 'Unknown Audio')
                functional_category = row.get('Functional Category', 'Other')
                source_path = row.get('Source File', '')
                timestamp = row.get('Timestamp', '')
                source_app = row.get('Source App/System', 'Unknown')
                forensic_relevance = row.get('Forensic Relevance', 'MEDIUM')
                
                if not source_path:
                    continue
                
                # Map to folder
                folder_name = map_audio_type_to_folder(audio_type)
                dest_dir = os.path.join(output_dir, folder_name)
                
                # Track attempt
                total_attempted += 1
                stats[folder_name]["attempted"] += 1
                
                # Copy file
                success, result = copy_audio_file(
                    source_path, dest_dir, audio_type, 
                    functional_category, timestamp, source_app
                )
                
                if success:
                    total_successful += 1
                    stats[folder_name]["successful"] += 1
                    print(f"✅ {audio_type}: {os.path.basename(result)}")
                else:
                    stats[folder_name]["failed"] += 1
                    errors.append(f"❌ {source_path}: {result}")
                    if len(errors) <= 10:  # Only show first 10 errors
                        print(f"❌ Failed: {os.path.basename(source_path)} - {result}")
                
                # Progress update every 25 files
                if total_attempted % 25 == 0:
                    print(f"Processed {total_attempted} files...")
                    
    except Exception as e:
        print(f"Error reading TSV file: {e}")
        sys.exit(1)
    
    # Generate summary report
    print(f"\n📊 Collection Summary")
    print(f"{'='*50}")
    print(f"Total files attempted: {total_attempted}")
    print(f"Total files successful: {total_successful}")
    print(f"Total files failed: {total_attempted - total_successful}")
    print(f"Success rate: {total_successful/total_attempted*100:.1f}%" if total_attempted > 0 else "0%")
    
    print(f"\n📁 By Category:")
    for category in categories:
        attempted = stats[category]["attempted"]
        successful = stats[category]["successful"]
        if attempted > 0:
            success_rate = successful / attempted * 100
            print(f"  {category}: {successful}/{attempted} ({success_rate:.1f}%)")
    
    # Save detailed report
    report_path = os.path.join(output_dir, "audio_collection_report.txt")
    with open(report_path, 'w') as f:
        f.write(f"Audio Collection Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Source TSV: {tsv_file}\n")
        f.write(f"Output Directory: {output_dir}\n\n")
        f.write(f"Summary:\n")
        f.write(f"Total files attempted: {total_attempted}\n")
        f.write(f"Total files successful: {total_successful}\n")
        f.write(f"Total files failed: {total_attempted - total_successful}\n\n")
        f.write(f"By Category:\n")
        for category in categories:
            attempted = stats[category]["attempted"]
            successful = stats[category]["successful"]
            if attempted > 0:
                f.write(f"{category}: {successful}/{attempted}\n")
        
        if errors:
            f.write(f"\nErrors:\n")
            for error in errors:
                f.write(f"{error}\n")
    
    print(f"\n📝 Detailed report saved: {report_path}")
    print(f"✨ Audio collection complete!")

if __name__ == "__main__":
    main()