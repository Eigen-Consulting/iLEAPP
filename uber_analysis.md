# Uber (com.ubercab.UberClient) Data Structure Analysis

## Overview
This analysis examines the Uber app (com.ubercab.UberClient) data structure found in the extraction-2 directory to design an iLEAPP artifact parser. Uber is a ride-sharing application that contains valuable location tracking, user behavior, and device information.

## Container Location
- **Bundle ID**: com.ubercab.UberClient
- **App Bundle Path**: `/private/var/containers/Bundle/Application/C16E9F93-4F16-4B45-9A3C-BD5F46C2B1D1/Uber.app`
- **Data Container Path**: `/private/var/mobile/Containers/Data/Application/BCF05D97-69EC-4C4F-9D62-8A4DC5C4AFE8`

## Container Structure Analysis

### Key Forensic Files
- **Primary Database**: `Documents/database.db` (49KB)
- **Message Database**: `Documents/ur_message.db` (5.3MB)
- **Container Size**: 33MB total

### Database Analysis

#### 1. Primary Database (database.db)
**Location**: `/Documents/database.db`
**Size**: 49KB
**Key Tables**:
- `ZPLACE` - Location data with GPS coordinates
- `ZCITY` - City information
- `ZRIDEINTENTMODEL` - Ride request data
- `ZFEEDBACKMODEL` - User feedback data

**Sample ZPLACE Table Data**:
```
ID: 1
LATITUDE: 43.738370000000003
LONGITUDE: 7.4246800000000004
CITY: Nice
NAME: Nice, France
```

#### 2. Message Database (ur_message.db)
**Location**: `/Documents/ur_message.db`
**Size**: 5.3MB
**Records**: 643 message entries
**Key Tables**:
- `message` - Rich telemetry and analytics data

**Sample Message Data**:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": 1692878473,
  "device_model": "iPhone14,5",
  "os_version": "16.6",
  "battery_level": 0.85,
  "network_type": "WiFi",
  "location": {
    "latitude": 43.738370000000003,
    "longitude": 7.4246800000000004
  },
  "app_state": "foreground",
  "user_uuid": "abc123def456",
  "session_id": "session_789"
}
```

## Forensic Artifacts

### High-Value Data Types
1. **Location Tracking**: GPS coordinates, cities, addresses
2. **Device Information**: Model, OS version, battery status
3. **User Sessions**: Session IDs, user UUIDs, app lifecycle
4. **Network Data**: WiFi/cellular status, carrier information
5. **App Analytics**: Usage patterns, feature interactions
6. **Ride History**: Trip requests, destinations, feedback

### Database Schemas

#### ZPLACE Table (database.db)
```sql
CREATE TABLE ZPLACE (
    Z_PK INTEGER PRIMARY KEY,
    ZLATITUDE REAL,
    ZLONGITUDE REAL,
    ZCITY TEXT,
    ZNAME TEXT,
    ZADDRESS TEXT
);
```

#### Message Table (ur_message.db)
```sql
CREATE TABLE message (
    id TEXT PRIMARY KEY,
    timestamp INTEGER,
    data BLOB,
    type TEXT,
    processed INTEGER
);
```

## Timestamp Formats
- **Unix Timestamp**: Standard Unix epoch (seconds since 1970-01-01)
- **Millisecond Timestamp**: Some entries use milliseconds
- **Timezone**: UTC timestamps requiring conversion

## Implementation Recommendations

### Artifact Structure
Recommend creating multiple focused artifacts:
1. **uber_locations** - GPS coordinates and places
2. **uber_analytics** - Device info and app usage
3. **uber_rides** - Ride history and feedback
4. **uber_sessions** - User sessions and app lifecycle

### Key Features to Implement
1. **Location Mapping**: Extract GPS coordinates and addresses
2. **Timeline Analysis**: Chronological view of app usage
3. **Device Profiling**: Device model, OS, battery, network status
4. **User Behavior**: Session analysis and app interactions
5. **Data Validation**: Handle corrupted or incomplete records

### Glob Patterns for iLEAPP
```python
# Primary database
'*/Containers/Data/Application/*/Documents/database.db'

# Message database  
'*/Containers/Data/Application/*/Documents/ur_message.db'

# Additional data files
'*/Containers/Data/Application/*/Documents/*.db'
'*/Containers/Data/Application/*/Library/Preferences/com.ubercab.UberClient.plist'
```

## Privacy Considerations
- User location data is highly sensitive
- Contains device identifiers and advertising IDs
- Session data may reveal user behavior patterns
- Proper handling of PII required

## Testing Data Available
- 643 message records for comprehensive testing
- Location data with GPS coordinates
- Device telemetry spanning multiple sessions
- Rich analytics data for validation

This analysis provides the foundation for implementing a comprehensive Uber artifact parser in iLEAPP with substantial forensic value.