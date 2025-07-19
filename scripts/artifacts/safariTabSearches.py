__artifacts_v2__ = {
    "get_safariTabSearches": {
        "name": "Safari - Tab Searches",
        "description": "Extracts search terms from Safari open tab titles",
        "author": "@claude-code",
        "version": "1.0",
        "date": "2025-07-19",
        "requirements": "none",
        "category": "Search & Web",
        "notes": "Identifies and extracts search queries from Safari tab titles",
        "paths": ('**/Safari/BrowserState.db*','**/Safari/CloudTabs.db*', '**/Safari/SafariTabs.db*'),
        "output_types": "standard"
    }
}

import datetime
import io
import nska_deserialize as nd
import sqlite3
import sys
import re
import plistlib
try:
    import biplist
except ImportError:
    biplist = None

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import artifact_processor, logfunc, tsv, timeline, is_platform_windows, open_sqlite_db_readonly


def is_search_term(title):
    """
    Determine if a tab title appears to be a search query.
    
    Args:
        title (str): The tab title to analyze
        
    Returns:
        bool: True if the title appears to be a search term, False otherwise
    """
    if not title or not isinstance(title, str):
        return False
    
    title = title.strip()
    
    # Skip empty titles
    if not title:
        return False
    
    # Skip titles that start with http/https
    if title.lower().startswith(('http://', 'https://')):
        return False
    
    # Skip titles that look like complete website names or domains
    if re.match(r'^[a-zA-Z0-9-]+\.(com|org|net|edu|gov|io|co|uk|de|fr|jp|cn)$', title.lower()):
        return False
        
    # Skip very long titles that look like full sentences or article titles
    # Search terms are typically short phrases
    if len(title) > 100:
        return False
    
    # Skip titles with too many sentence-like characteristics
    # Complex sentences usually have multiple clauses, punctuation
    sentence_indicators = ['.', '!', '?', ';', ':', '"', "'", '(', ')', '[', ']']
    # Special handling for dashes and commas in news/media titles
    dash_comma_indicators = ['-', ',', '&']
    
    punctuation_count = sum(1 for char in title if char in sentence_indicators)
    dash_comma_count = sum(1 for char in title if char in dash_comma_indicators)
    
    # If there's too much punctuation, it's probably not a search term
    if punctuation_count > 1 or dash_comma_count > 2:
        return False
    
    # Skip titles that look like complete sentences (have articles, prepositions, etc.)
    common_sentence_words = [
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
        'of', 'with', 'by', 'from', 'about', 'into', 'through', 'during', 'before', 'after',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'will', 'would', 'could', 'should'
    ]
    
    words = title.lower().split()
    sentence_word_count = sum(1 for word in words if word in common_sentence_words)
    
    # If more than 25% of words are common sentence words, probably not a search term
    # Also, if there are many sentence words in absolute terms, it's likely a sentence
    if len(words) > 0 and ((sentence_word_count / len(words)) > 0.25 or sentence_word_count >= 3):
        return False
    
    # Skip obvious website titles or branded pages
    website_indicators = [
        'homepage', 'home page', 'welcome to', 'official site', 'website', 
        'sign in', 'log in', 'login', 'register', 'sign up', 'breaking news',
        'news,', 'multimedia'
    ]
    
    title_lower = title.lower()
    if any(indicator in title_lower for indicator in website_indicators):
        return False
    
    # Skip classic sentence patterns
    # If it has 8+ words and ends with period, likely a sentence
    if len(words) >= 8 and title.endswith('.'):
        return False
    
    # Skip news-style titles (multiple capitalized words with dashes/commas)
    if dash_comma_count >= 2 and len([w for w in title.split() if w and w[0].isupper()]) >= 4:
        return False
    
    # If we get here, it's likely a search term
    return True


@artifact_processor
def get_safariTabSearches(files_found, report_folder, seeker, wrap_text, timezone_offset):
    data_list = []
    
    for file_found in files_found:
        file_found = str(file_found)
        
        if not file_found.endswith('.db'):
            continue
        
        # Handle BrowserState.db (local tabs)
        if 'BrowserState' in file_found:
            try:
                db = open_sqlite_db_readonly(file_found)
                cursor = db.cursor()

                cursor.execute("""
                select
                datetime(last_viewed_time+978307200,'unixepoch'), 
                title, 
                url, 
                user_visible_url, 
                opened_from_link, 
                private_browsing
                from
                tabs
                where title IS NOT NULL
                """)

                all_rows = cursor.fetchall()
                if all_rows:
                    for row in all_rows:
                        timestamp, title, url, user_visible_url, opened_from_link, private_browsing = row
                        
                        # Check if this title appears to be a search term
                        if is_search_term(title):
                            data_list.append((
                                timestamp, 
                                title, 
                                url, 
                                user_visible_url, 
                                opened_from_link, 
                                private_browsing,
                                'Local Tab',
                                file_found
                            ))
                
                db.close()
                
            except Exception as ex:
                logfunc(f'Error processing BrowserState.db {file_found}: {str(ex)}')
            
        # Handle CloudTabs.db (iCloud synced tabs)
        elif 'CloudTabs' in file_found:
            try:
                db = open_sqlite_db_readonly(file_found)
                cursor = db.cursor()

                cursor.execute("""
                select
                cloud_tabs.system_fields,
                cloud_tabs.title,
                cloud_tabs.url,
                cloud_tab_devices.device_name,
                cloud_tabs.device_uuid,
                cloud_tabs.tab_uuid
                from cloud_tabs
                left join cloud_tab_devices on cloud_tab_devices.device_uuid = cloud_tabs.device_uuid
                where cloud_tabs.title IS NOT NULL
                """)

                all_rows = cursor.fetchall()
                if all_rows:
                    for row in all_rows:
                        system_fields, title, url, device_name, device_uuid, tab_uuid = row
                        
                        # Check if this title appears to be a search term
                        if is_search_term(title):
                            created_timestamp = None
                            modified_timestamp = None
                            mod_dev = None
                            
                            # Parse system_fields plist if available
                            if system_fields:
                                try:
                                    plist_file_object = io.BytesIO(system_fields)
                                    if system_fields.find(b'NSKeyedArchiver') == -1:
                                        if sys.version_info >= (3, 9):
                                            plist = plistlib.load(plist_file_object)
                                        else:
                                            plist = biplist.readPlist(plist_file_object) if biplist else None
                                    else:
                                        plist = nd.deserialize_plist(plist_file_object)
                                    
                                    if plist:
                                        for x in plist:
                                            for keys, values in x.items():
                                                if keys == 'RecordCtime':
                                                    created_timestamp = values
                                                if keys == 'RecordMtime':
                                                    modified_timestamp = values
                                                if keys == 'ModifiedByDevice':
                                                    mod_dev = values
                                except Exception as ex:
                                    logfunc(f'Failed to parse cloud tab plist: {str(ex)}')
                            
                            data_list.append((
                                created_timestamp or modified_timestamp,
                                title,
                                url,
                                device_name or 'Unknown Device',
                                'Yes',  # opened_from_link equivalent
                                'No',   # private_browsing equivalent  
                                'iCloud Tab',
                                file_found
                            ))
                
                db.close()
                
            except Exception as ex:
                logfunc(f'Error processing CloudTabs.db {file_found}: {str(ex)}')
    
    if data_list:
        # Sort by timestamp (most recent first)
        data_list.sort(key=lambda x: x[0] or '', reverse=True)
        
        data_headers = (
            'Timestamp',
            'Search Term', 
            'URL',
            'User Visible URL/Device',
            'Opened from Link',
            'Private Browsing',
            'Tab Type',
            'Source File'
        )
        
        return data_headers, data_list, file_found
    else:
        logfunc('No Safari tab search terms found')
        return (), [], ''