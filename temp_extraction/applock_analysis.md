# AppLock Security App (com.domobile.applock) - Technical Analysis

## Executive Summary

The AppLock Security App (com.domobile.applock) is a privacy protection application that allows users to lock individual apps and create secure media vaults. This analysis examines the forensic artifacts from version 1.2.6 (build 2024041201) running on iOS 17.5.1.

## Container Location

**Path:** `/private/var/mobile/Containers/Data/Application/32D7F586-5A6D-48F2-8B00-1D67ACEFEAD5/`

**Bundle ID:** `com.domobile.applock`

**App Version:** 1.2.6 (2024041201)

## Database Analysis

### 1. Main Application Database (AppLock.db)

**Location:** `Documents/AppLock.db`

**Size:** 20,480 bytes (20 KB)

**Schema:**
```sql
CREATE TABLE sAlbum (
    _id INTEGER PRIMARY KEY AUTOINCREMENT,
    albumId TEXT,
    name TEXT,
    mediaId TEXT,
    lastTime INTEGER,
    attach TEXT,
    sort INTEGER
);

CREATE TABLE sMedia (
    _id INTEGER PRIMARY KEY AUTOINCREMENT,
    mediaId TEXT,
    albumId TEXT,
    mimeType TEXT,
    srcAlbum TEXT,
    srcSmart INTEGER,
    fileName TEXT,
    fileSize INTEGER,
    width INTEGER,
    height INTEGER,
    duration TEXT,
    fromId INTEGER,
    lastTime INTEGER,
    lastModified INTEGER,
    attach TEXT,
    sort INTEGER
);

CREATE TABLE web_bookmarks (
    _id INTEGER PRIMARY KEY AUTOINCREMENT,
    bookmarkId TEXT,
    url TEXT,
    name TEXT,
    lastTime INTEGER,
    sort TEXT
);
```

**Current Data:**
- **sAlbum table:** 1 record (default album: "defAlbum" created at timestamp 1724159279027)
- **sMedia table:** 0 records
- **web_bookmarks table:** 0 records

### 2. Cache Database (Cache.db)

**Location:** `Library/Caches/com.domobile.applock/Cache.db`

**Size:** 262,144 bytes (256 KB)

**Schema:** Standard CFNetwork URL cache database with tables:
- `cfurl_cache_response`
- `cfurl_cache_blob_data`
- `cfurl_cache_receiver_data`

**Current Data:** 8 cached HTTP responses

### 3. Additional Databases

**Complete Database Inventory:**
1. `Documents/AppLock.db` (20 KB) - Main app database
2. `Library/Caches/com.domobile.applock/Cache.db` (256 KB) - HTTP cache
3. `Library/Caches/.inmobi_10.7.1/database/inMobi.sqlite` - Ad SDK database
4. `Library/Caches/com.bytedance.pagadsdk.root/tracker.sqlite` - ByteDance ad tracking
5. `Library/Caches/com.vungle/*/cleverCache/Cache.db` - Vungle ad cache
6. `Library/Caches/mvsdk.db` - Mintegral ad SDK
7. `Library/Caches/WebKit/AlternativeServices/AlternativeService.sqlite` - WebKit cache
8. `Library/HTTPStorages/com.domobile.applock/httpstorages.sqlite` - HTTP storage
9. `Library/sgmlogger.sqlite` - Logging database
10. `Library/WebKit/WebsiteData/ResourceLoadStatistics/observations.db` - WebKit statistics
11. `SystemData/com.apple.SafariViewService/Library/WebKit/WebsiteData/AlternativeService.sqlite` - Safari view service
12. `SystemData/com.apple.SafariViewService/Library/WebKit/WebsiteData/observations.db` - Safari observations

## Key Forensic Artifacts

### 1. Protected Media Vault

**Location:** `Documents/Vault/Medias/`

**Structure:**
- Media files are stored in timestamped folders (e.g., `1724159682830030/`, `1724159694064002/`, `1724159843301007/`)
- Each folder contains a `config.kv` file (XML plist format) that maps media IDs to filenames
- Example mapping found:
  - ID "1" → `IMG_0004.HEIC`
  - ID "9" → `IMG_0004.MOV`

**Forensic Significance:** This vault contains user-protected media files that were moved from the device's Photos app into the AppLock secure storage.

### 2. App Configuration (com.domobile.applock.plist)

**Location:** `Library/Preferences/com.domobile.applock.plist`

**Key Settings Found:**
- `applock_initialed`: App initialization status
- `number_password`: Indicates use of numeric passcode
- `appleid_setup_alert`: Apple ID setup alert status
- `config_accept_privacy_policy`: Privacy policy acceptance
- `start_session_timestamp`: Session tracking
- `app_running_time`: App usage tracking
- `settings_fetch_time`: Configuration sync timestamps
- `flex_cache_dir`: UI flex cache directory (`flex_2024041201`)

**Advertising/Tracking Data:**
- Multiple ad SDK configurations (InMobi, ByteDance, Vungle, Mintegral, AppLovin)
- User agent strings
- Device identifiers
- Ad targeting parameters
- GDPR consent data

### 3. Security Features Analysis

**User Authentication:**
- Numeric password/PIN protection
- No biometric authentication artifacts found
- Session management with timeout tracking

**Protected Content:**
- Media vault for photos and videos
- Web bookmarks protection (unused in this sample)
- Album organization system

**Privacy Controls:**
- Privacy policy acceptance tracking
- GDPR compliance features
- Consent management for advertising

## Technical Timestamps

All timestamps in the AppLock database appear to use Unix epoch milliseconds format:
- Default album created: `1724159279027` (August 20, 2024 13:07:59.027 UTC)
- Media vault folders: `1724159682830030`, `1724159694064002`, `1724159843301007`

## Security Implications

1. **Data Protection:** Media files are moved to app-specific container, making them inaccessible through standard Photos app
2. **Authentication:** Numeric PIN protection prevents unauthorized access
3. **Privacy:** Extensive ad tracking and analytics data collection
4. **Forensic Value:** Protected media vault contains user's sensitive content

## Recommendations for iLEAPP Implementation

1. **Primary Artifact:** Parse `AppLock.db` to extract protected album and media information
2. **Secondary Artifacts:** 
   - Parse vault media configurations
   - Extract app settings from preferences plist
   - Analyze usage patterns from session data
3. **Timestamp Conversion:** Convert Unix epoch milliseconds to human-readable format
4. **Output Categories:** 
   - Protected Media Albums
   - Secure Media Files
   - App Configuration & Settings
   - Usage Analytics

## File System Layout

```
32D7F586-5A6D-48F2-8B00-1D67ACEFEAD5/
├── Documents/
│   ├── AppLock.db                     # Main database
│   ├── Vault/
│   │   └── Medias/
│   │       ├── 1724159682830030/
│   │       ├── 1724159694064002/
│   │       └── 1724159843301007/
│   │           └── config.kv          # Media mapping
│   └── flex_2024041201/               # UI components
├── Library/
│   ├── Caches/
│   │   └── com.domobile.applock/
│   │       └── Cache.db               # HTTP cache
│   └── Preferences/
│       └── com.domobile.applock.plist # App settings
└── [Additional system files...]
```

## Analysis Date

Generated: July 17, 2025