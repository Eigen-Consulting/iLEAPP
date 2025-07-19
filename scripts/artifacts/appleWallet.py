__artifacts_v2__ = {
    "applewallet": {
        "name": "Apple Wallet Payment Cards",
        "description": "Apple Wallet Payment Cards - Last 4 digits and card identifiers",
        "author": "@claude",
        "version": "1.0",
        "date": "2025-07-19",
        "requirements": "none",
        "category": "Finance & Purchase",
        "notes": "Extracts payment card information from PassKit database",
        "paths": ('*/mobile/Library/Passes/passes*.sqlite*',),
        "output_types": "all",
        "artifact_icon": "credit_card",
    }
}

from scripts.ilapfuncs import artifact_processor, get_file_path, get_sqlite_db_records


@artifact_processor
def applewallet(files_found, report_folder, seeker, wrap_text, timezone_offset):
    source_path = get_file_path(files_found, 'passes*.sqlite')
    data_list = []

    query = '''
    SELECT 
        payment_application.dpan_suffix as last_four_digits,
        pass.primary_account_identifier as card_identifier,
        pass.organization_name as card_issuer,
        payment_application.display_name as display_name,
        payment_application.payment_network_identifier as network_id,
        payment_application.state as application_state
    FROM payment_application 
    LEFT JOIN pass ON payment_application.pass_pid = pass.pid
    WHERE payment_application.dpan_suffix IS NOT NULL
    '''

    data_headers = (
        'Last 4 Digits',
        'Card Issuer/Identifier', 
        'Card Issuer',
        'Display Name',
        'Payment Network ID',
        'Application State'
    )

    db_records = get_sqlite_db_records(source_path, query)

    for record in db_records:
        data_list.append((
            record[0],  # last_four_digits
            record[1],  # card_identifier  
            record[2],  # card_issuer
            record[3],  # display_name
            record[4],  # network_id
            record[5]   # application_state
        ))

    return data_headers, data_list, source_path