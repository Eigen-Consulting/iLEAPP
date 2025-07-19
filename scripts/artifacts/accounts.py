__artifacts_v2__ = {
    'accounts': {
        'name': 'Apple Accounts',
        'description': 'Identifies primary Apple ID from iCloud account configuration',
        'author': '@iLEAPP',
        'creation_date': '2025-07-19',
        'last_update_date': '2025-07-19',
        'requirements': 'none',
        'category': 'Account',
        'notes': 'Extracts Apple ID information from Accounts3.sqlite, specifically targeting iCloud accounts',
        'paths': ('**/Accounts3.sqlite',),
        'output_types': 'standard',
        'artifact_icon': 'user'
    }
}

from scripts.ilapfuncs import artifact_processor, get_file_path, get_sqlite_db_records

@artifact_processor
def accounts(files_found, report_folder, seeker, wrap_text, timezone_offset):
    source_path = get_file_path(files_found, 'Accounts3.sqlite')
    data_list = []

    query = '''
    SELECT ZUSERNAME, ZACCOUNTDESCRIPTION 
    FROM ZACCOUNT 
    WHERE ZACCOUNTDESCRIPTION = 'iCloud'
    '''

    data_headers = (
        'Account Description',
        'Username / Apple ID'
    )

    db_records = get_sqlite_db_records(source_path, query)

    for record in db_records:
        data_list.append((record['ZACCOUNTDESCRIPTION'], record['ZUSERNAME']))

    return data_headers, data_list, source_path