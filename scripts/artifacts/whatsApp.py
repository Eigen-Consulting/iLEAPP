__artifacts_v2__ = {
    'whatsAppCallHistory': {
        'name': 'WhatsApp - Call History',
        'description': 'Extract call history from WhatsApp',
        'author': '@Vinceckert',
        'creation_date': '2024-05-31',
        'last_update_date': '2025-04-08',
        'requirements': 'none',
        'category': 'WhatsApp',
        'notes': '',
        'paths': (
            '*/mobile/Containers/Shared/AppGroup/*/CallHistory.sqlite*',
            '*/mobile/Containers/Shared/AppGroup/*/ContactsV2.sqlite*',
        ),
        'output_types': 'standard',
        'artifact_icon': 'user',
    },
    'whatsAppMessages': {
        'name': 'WhatsApp - Messages',
        'description': 'Extract WhatsApp messages',
        'author': '@AlexisBrignoni',
        'creation_date': '2021-03-26',
        'last_update_date': '2025-05-13',
        'requirements': '',
        'category': 'WhatsApp',
        'notes': '',
        'paths': (
            '*/mobile/Containers/Shared/AppGroup/*/ChatStorage.sqlite*',
            '*/mobile/Containers/Shared/AppGroup/*/Message/Media/*/*/*/*'),
        'output_types': 'all',
        'artifact_icon': 'message-square'
    },
    'whatsAppContacts': {
        'name': 'WhatsApp - Contacts',
        'description': 'Extract contacts registered in WhatsApp',
        'author': '@AlexisBrignoni',
        'creation_date': '2021-03-26',
        'last_update_date': '2025-04-08',
        'requirements': '',
        'category': 'WhatsApp',
        'notes': '',
        'paths': ('*/mobile/Containers/Shared/AppGroup/*/ContactsV2.sqlite*',),
        'output_types': ['html', 'tsv', 'lava'],
        'artifact_icon': 'users'
    },
    'whatsAppMessageGapAnalysis': {
        'name': 'WhatsApp - Message Gap Analysis',
        'description': 'Analyze primary key gaps in WhatsApp messages to detect deleted messages',
        'author': '@assistant',
        'creation_date': '2025-07-19',
        'last_update_date': '2025-07-19',
        'requirements': '',
        'category': 'WhatsApp',
        'notes': 'Identifies deleted messages by analyzing gaps in Z_PK sequence',
        'paths': ('*/mobile/Containers/Shared/AppGroup/*/ChatStorage.sqlite*',),
        'output_types': ['html', 'tsv', 'lava'],
        'artifact_icon': 'alert-triangle'
    }
}


import inspect
import blackboxprotobuf

from pathlib import Path
from scripts.ilapfuncs import artifact_processor, \
    get_file_path, get_sqlite_db_records, attach_sqlite_db_readonly, \
    check_in_media, convert_cocoa_core_data_ts_to_utc, logfunc
from scripts.aggregation_engine import AggregationEngine


@artifact_processor
def whatsAppCallHistory(files_found, report_folder, seeker, wrap_text, timezone_offset):
    source_path = get_file_path(files_found, 'CallHistory.sqlite')
    contacts_db = get_file_path(files_found, 'ContactsV2.sqlite')

    data_list = []

    contact_info = '''
        ,base2.ZFULLNAME,
        base2.ZPHONENUMBER
    '''

    tables_join = '''
    INNER JOIN ContactsV2.ZWAADDRESSBOOKCONTACT base2 ON ZWACDCALLEVENTPARTICIPANT.ZJIDSTRING = base2.ZWHATSAPPID
    '''

    query = f'''
    SELECT
        ZWACDCALLEVENT.ZDATE,
        ZWACDCALLEVENT.ZDATE + ZWACDCALLEVENT.ZDURATION AS 'Datetime_end', 
        time(ZWACDCALLEVENT.ZDURATION, 'unixepoch') AS 'Duration',
        CASE
            WHEN ZWACDCALLEVENT.ZGROUPCALLCREATORUSERJIDSTRING = ZWACDCALLEVENTPARTICIPANT.ZJIDSTRING then 'Incoming' 
            ELSE 'Outgoing'
        END Direction,
        CASE ZWACDCALLEVENT.ZOUTCOME
            WHEN 0 THEN 'Ended'
            WHEN 1 THEN 'Missed'
            WHEN 4 THEN 'Rejected'
            ELSE ZWACDCALLEVENT.ZOUTCOME
        END Disconnected_cause,
        ZWACDCALLEVENTPARTICIPANT.ZJIDSTRING as 'Contact ID'
        {contact_info if contacts_db else ''}
    FROM ZWACDCALLEVENT, ZWACDCALLEVENTPARTICIPANT
    {tables_join if contacts_db else ''}
    WHERE ZWACDCALLEVENT.Z1CALLEVENTS = ZWACDCALLEVENTPARTICIPANT.Z1PARTICIPANTS
    '''
    data_headers = [
        ('Starting Timestamp', 'datetime'),
        ('Ending Timestamp', 'datetime'),
        'Duration H:M:S',
        'Direction',
        'Disconnected cause',
        'Contact ID']

    if contacts_db:
        attach_query = attach_sqlite_db_readonly(contacts_db, 'ContactsV2')
        db_records = get_sqlite_db_records(source_path, query, attach_query)
        data_headers.extend(
            ['Contact Fullname', ('Phone Number', 'phonenumber')])
    else:
        db_records = get_sqlite_db_records(source_path, query)

    for record in db_records:
        start_time = convert_cocoa_core_data_ts_to_utc(record[0])
        end_time = convert_cocoa_core_data_ts_to_utc(record[1])

        record_data = [
            start_time, end_time, record[2], record[3], record[4], record[5]]
        if contacts_db:
            record_data.extend([record[6], record[7]])
        data_list.append(
            tuple(record_data))

    data_headers = tuple(data_headers)
    return data_headers, data_list, source_path


@artifact_processor
def whatsAppContacts(files_found, report_folder, seeker, wrap_text, timezone_offset):
    source_path = get_file_path(files_found, 'ContactsV2.sqlite')
    data_list = []

    query = '''
    SELECT
        ZFULLNAME,
        ZABOUTTEXT,
        ZABOUTTIMESTAMP,
        ZPHONENUMBER,
        ZPHONENUMBERLABEL,
        ZWHATSAPPID,
        ZIDENTIFIER
    FROM ZWAADDRESSBOOKCONTACT
    '''

    data_headers = (
        'Fullname',
        'About Text',
        ('About Text Timestamp', 'datetime'),
        ('Phone Number', 'phonenumber'),
        'Phone Number Label',
        'Whatsapp ID',
        'Identifier')

    db_records = get_sqlite_db_records(source_path, query)

    for record in db_records:

        about_timestamp = convert_cocoa_core_data_ts_to_utc(
            record['ZABOUTTIMESTAMP'])
        phone_number_label = record['ZPHONENUMBERLABEL']
        cleaned_label = phone_number_label.replace('_$!<', '').replace(
            '>!$_', '') if phone_number_label else ''

        data_list.append(
            (record[0], record[1], about_timestamp, record[3],
             cleaned_label, record[5], record[6]))

    return data_headers, data_list, source_path


@artifact_processor
def whatsAppMessages(files_found, report_folder, seeker, wrap_text, timezone_offset):
    artifact_info = inspect.stack()[0]
    source_path = get_file_path(files_found, 'ChatStorage.sqlite')
    data_list = []

    query = '''
    SELECT
        ZMESSAGEDATE,
        ZISFROMME,
        ZPARTNERNAME,
        ZFROMJID,
        ZTOJID,
        ZWAMESSAGE.ZMEDIAITEM,
        ZTEXT,
        ZSTARRED,
        ZMESSAGETYPE,
        ZLONGITUDE,
        ZLATITUDE,
        ZMEDIALOCALPATH,
        ZXMPPTHUMBPATH,
        ZMETADATA
    FROM ZWAMESSAGE
    LEFT JOIN ZWAMEDIAITEM ON ZWAMESSAGE.Z_PK = ZWAMEDIAITEM.ZMESSAGE 
    LEFT JOIN ZWACHATSESSION ON ZWACHATSESSION.Z_PK = ZWAMESSAGE.ZCHATSESSION
    '''

    data_headers = (
        ('Timestamp', 'datetime'), 'Sender Name', 'From ID', 'Receiver', 'To ID',
        'Message', ('Attachment File', 'media'), ('Thumb', 'media'),
        'Starred?', 'Number of Forwardings', 'Forwarded from',
        'Latitude', 'Longitude',)

    db_records = get_sqlite_db_records(source_path, query)

    for record in db_records:
        message_date = convert_cocoa_core_data_ts_to_utc(
            record['ZMESSAGEDATE'])

        sender = 'Local User' if record['ZISFROMME'] == 1 else record['ZPARTNERNAME']
        receiver = record['ZPARTNERNAME'] if record['ZISFROMME'] == 1 else 'Local User'

        attach_file = ''
        media_local_path = record['ZMEDIALOCALPATH']
        if media_local_path:
            attach_file_name = Path(media_local_path).name
            attach_file = check_in_media(media_local_path, attach_file_name)

        thumb = ''
        thumb_path = record['ZXMPPTHUMBPATH']
        if thumb_path:
            thumb_name = Path(thumb_path).name
            thumb = check_in_media(thumb_path, thumb_name)

        metadata = record['ZMETADATA']
        number_forward = ''
        from_forward = ''
        if metadata:
            try:
                decoded_data, _ = blackboxprotobuf.decode_message(metadata)
                number_forward = f'{decoded_data.get("17")}'
                from_forward = f'{decoded_data.get("21").decode("utf-8")}'
            except:
                pass

        lon = record['ZLONGITUDE'] if record['ZMESSAGETYPE'] == 5 else ''
        lat = record['ZLATITUDE'] if record['ZMESSAGETYPE'] == 5 else ''

        data_list.append((message_date, sender, record['ZFROMJID'], receiver, record['ZTOJID'],
                          record['ZTEXT'], attach_file, thumb, record['ZSTARRED'],
                          number_forward, from_forward, lat, lon,))

    # Report messaging statistics to aggregation engine
    if data_list:
        AggregationEngine.report_messaging_count("WhatsApp", len(data_list))

    return data_headers, data_list, source_path


@artifact_processor
def whatsAppMessageGapAnalysis(files_found, report_folder, seeker, wrap_text, timezone_offset):
    """
    Analyze primary key gaps in WhatsApp ZWAMESSAGE table to detect deleted messages.
    This function identifies gaps in the Z_PK sequence which indicate deleted messages.
    """
    source_path = get_file_path(files_found, 'ChatStorage.sqlite')
    data_list = []

    # Query to get all primary keys in order
    query = '''
    SELECT Z_PK
    FROM ZWAMESSAGE
    ORDER BY Z_PK ASC
    '''

    data_headers = (
        'Gap Range',
        'Missing Messages Count',
        'Gap Start Z_PK',
        'Gap End Z_PK',
        'Gap Description'
    )

    db_records = get_sqlite_db_records(source_path, query)

    if not db_records:
        # No messages found, return empty data
        return data_headers, data_list, source_path

    # Extract Z_PK values into a list
    primary_keys = [record['Z_PK'] for record in db_records]

    # Initialize counters
    total_missing_messages = 0
    gap_number = 1

    # Analyze gaps in primary key sequence
    for i in range(len(primary_keys) - 1):
        current_pk = primary_keys[i]
        next_pk = primary_keys[i + 1]

        # Check if there's a gap (difference > 1)
        if next_pk - current_pk > 1:
            gap_size = next_pk - current_pk - 1
            total_missing_messages += gap_size

            gap_range = f"Gap {gap_number}"
            gap_description = f"Messages with Z_PK between {current_pk} and {next_pk} are missing"

            data_list.append((
                gap_range,
                gap_size,
                current_pk + 1,  # First missing Z_PK
                next_pk - 1,     # Last missing Z_PK
                gap_description
            ))

            gap_number += 1

    # Add summary row at the top
    if total_missing_messages > 0:
        summary_row = (
            "TOTAL SUMMARY",
            total_missing_messages,
            "N/A",
            "N/A",
            f"Total deleted messages detected: {total_missing_messages}"
        )
        data_list.insert(0, summary_row)
    else:
        # No gaps found
        no_gaps_row = (
            "NO GAPS DETECTED",
            0,
            "N/A",
            "N/A",
            "No deleted messages detected in the primary key sequence"
        )
        data_list.append(no_gaps_row)

    return data_headers, data_list, source_path
