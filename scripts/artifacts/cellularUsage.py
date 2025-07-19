__artifacts_v2__ = {
    "cellularUsage": {
        "name": "Cellular Usage Info",
        "description": "Extracts raw SIM card last update time from CellularUsage database",
        "author": "@claude",
        "version": "1.0",
        "date": "2025-07-19",
        "requirements": "none",
        "category": "Network",
        "notes": "Provides both raw and converted timestamp values for SIM card last update time",
        "paths": ('*/wireless/Library/Databases/CellularUsage.db*',),
        "output_types": "standard",
        "artifact_icon": "settings"
    }
}

from scripts.ilapfuncs import artifact_processor, get_sqlite_db_records, convert_cocoa_core_data_ts_to_utc

@artifact_processor
def cellularUsage(files_found, report_folder, seeker, wrap_text, timezone_offset):
    data_list = []
    db_file = ''
    db_records = []

    query = '''
    SELECT last_update_time
    FROM subscriber_info
    '''

    for file_found in files_found:
        if file_found.endswith('CellularUsage.db'):
            db_file = file_found
            db_records = get_sqlite_db_records(db_file, query)
            break

    for record in db_records:
        raw_timestamp = record[0]
        converted_timestamp = convert_cocoa_core_data_ts_to_utc(record[0])
        data_list.append((raw_timestamp, converted_timestamp, db_file))

    data_headers = (
        'Raw Last Update Time',
        ('Last Update Time (UTC)', 'datetime'),
        'Source File'
    )
    
    return data_headers, data_list, db_file