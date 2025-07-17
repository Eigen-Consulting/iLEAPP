# Wickr App (com.mywickr.wickr) - Technical Analysis for iLEAPP Implementation

## Executive Summary

This analysis examines the Wickr Enterprise (com.mywickr.wickr) application data structure from a forensic perspective to design comprehensive iLEAPP artifact parsers. **Critical Finding: No traditional databases or unencrypted message content found**, but significant forensic metadata artifacts are available that provide investigative value.

## 1. Application Structure Overview

### Bundle Identifier
- **Primary**: com.mywickr.wickr
- **App Name**: Wickr Me / WickrEnterprise
- **Version**: 6.4.2 (Build: 600400200001)

### Key Container Locations
1. **Main App Data Container**: `/private/var/mobile/Containers/Data/Application/B5E61979-213D-4433-B5BF-4ACA32FFBAD4/`
2. **App Group Container**: `/private/var/mobile/Containers/Shared/AppGroup/D36C4D49-08CF-4DB7-9951-7AE940325EBA/`
3. **Service Extension Container**: `/private/var/mobile/Containers/Data/PluginKitPlugin/18D9F204-EE27-4888-8B44-5916AF54033C/`
4. **App Bundle**: `/private/var/containers/Bundle/Application/0A9DA716-5318-412F-B443-51980B85A3AB/WickrEnterprise.app/`
5. **iCloud Container**: `/private/var/mobile/Library/Mobile Documents/iCloud~com~mywickr~wickr/`

## 2. Data Structure Analysis

### Critical Finding: No SQLite Databases
- **No message databases found**: Unlike most messaging apps, Wickr does not store traditional SQLite databases with message content
- **No contact lists**: No persistent contact storage detected
- **No media files**: No cached media files found in expected locations
- **Encryption by Design**: This aligns with Wickr's security model of ephemeral messaging

### Available Forensic Artifacts

#### 2.1 Configuration Files (HIGH FORENSIC VALUE)
1. **Main Preferences** - `Library/Preferences/com.mywickr.wickr.plist`
   - Binary plist containing user settings
   - Theme preferences (light/dark mode)
   - Feature toggles (markdown, call status, video calls)
   - Network migration status
   - User ID references

2. **App Group Preferences** - `Library/Preferences/group.com.mywickr.wickr.plist`
   - Shared preferences between app and extensions
   - Notification extension settings
   - App state indicators
   - Key rotation status

3. **Network Extension Preferences** - `Library/Preferences/com.wickr.networkExtension.plist`
   - VPN/Network extension configuration

#### 2.2 Push Notification Configuration (HIGH FORENSIC VALUE)
- **Location**: `Documents/pushConfig.plist`
- **Contains**: 
  - Censorship proxy configuration
  - Server list URLs (Base64 encoded)
  - Certificate information
  - Voice/video hosts configuration
  - Forensic significance: Network infrastructure and communication endpoints

#### 2.3 Crash Reports and Analytics (MEDIUM FORENSIC VALUE)
- **Bugsnag Crash Reports**: `Library/Application Support/com.bugsnag.Bugsnag/com.mywickr.wickr/v1/`
  - User device information (timezone, device specs)
  - App usage breadcrumbs with timestamps
  - Error reports and app state changes
  - Navigation controller references

#### 2.4 App Usage Analytics (MEDIUM FORENSIC VALUE)
- **Countly Analytics**: `Library/Application Support/Countly.dat`
  - Binary file containing usage statistics
  - Requires specialized parsing

#### 2.5 UI Screenshots (LOW FORENSIC VALUE)
- **SplashBoard Snapshots**: `Library/SplashBoard/Snapshots/`
  - App interface screenshots (.ktx files)
  - Limited forensic value but may show app state

## 3. Timestamp Analysis

### Format: ISO 8601 UTC
- **Standard Format**: `2023-02-21T17:04:36.829Z`
- **Timezone**: UTC (Z suffix)
- **Precision**: Milliseconds
- **Sources**: Bugsnag breadcrumbs, crash reports

### Available Timestamps
1. **App Launch**: Bugsnag loaded events
2. **UI State Changes**: Window visibility, orientation changes
3. **Navigation Events**: Controller lifecycle events
4. **App Background/Foreground**: State transitions

## 4. Encryption and Security Indicators

### Encryption Evidence
1. **No Plaintext Messages**: Complete absence of message content
2. **Ephemeral Storage**: No persistent message storage
3. **Cryptographic Frameworks**: WickrCryptoC.framework, WickrDB.framework
4. **Key Rotation**: Evidence of key rotation processes in preferences

### Security Features Detected
- Face ID authentication support
- VoIP encryption capabilities
- Network extension for secure communication
- Certificate pinning configuration

## 5. User Behavior and Metadata Patterns

### Available Behavioral Indicators
1. **App Usage Patterns**: Launch times, session duration (from breadcrumbs)
2. **Feature Usage**: Settings preferences indicate used features
3. **Network Activity**: Push configuration reveals server connections
4. **Device Information**: Hardware specs, timezone, OS version

### Metadata Sources
- Device timezone (CET detected)
- App version and build information
- Feature flag states
- Network configuration parameters

## 6. Forensic Artifact Implementation Recommendations

### 6.1 High-Priority Artifacts

#### A. Wickr Configuration Parser
- **Target Files**: `*.plist` files in preferences and documents
- **Forensic Value**: User settings, feature usage, network configuration
- **Implementation**: Binary plist parser with key extraction

#### B. Push Configuration Parser
- **Target Files**: `pushConfig.plist`, `Documents/pushConfig.plist`
- **Forensic Value**: Server endpoints, network infrastructure
- **Implementation**: JSON parser with Base64 decoding

#### C. Crash Analytics Parser
- **Target Files**: Bugsnag JSON files, breadcrumbs
- **Forensic Value**: Usage patterns, timestamps, device info
- **Implementation**: JSON parser with timestamp conversion

### 6.2 Medium-Priority Artifacts

#### D. App Usage Analytics Parser
- **Target Files**: `Countly.dat`
- **Forensic Value**: Detailed usage statistics
- **Implementation**: Binary parser (requires reverse engineering)

#### E. Container Metadata Parser
- **Target Files**: `.com.apple.mobile_container_manager.metadata.plist`
- **Forensic Value**: App installation info, container relationships
- **Implementation**: Binary plist parser

### 6.3 Low-Priority Artifacts

#### F. UI State Parser
- **Target Files**: SplashBoard snapshots
- **Forensic Value**: App interface states
- **Implementation**: KTX texture file parser

## 7. Implementation Challenges and Limitations

### Major Challenges
1. **No Traditional Database**: No SQLite schemas to parse
2. **Binary Plist Format**: Requires proper plist parsing
3. **Encrypted Content**: No message content available
4. **Binary Analytics**: Countly.dat requires reverse engineering

### Limitations
1. **Message Content**: Will never be recoverable due to encryption
2. **Contact Lists**: No persistent storage of contacts
3. **Media Files**: No cached media files
4. **Communication Logs**: No traditional call/message logs

## 8. Recommended iLEAPP Artifacts

### Artifact 1: Wickr Configuration
- **Name**: "Wickr - App Configuration"
- **Description**: "User preferences, feature settings, and app configuration"
- **Paths**: `*/com.mywickr.wickr.plist`, `*/group.com.mywickr.wickr.plist`
- **Category**: "Messaging"

### Artifact 2: Wickr Network Configuration
- **Name**: "Wickr - Network Configuration"
- **Description**: "Push service configuration, server endpoints, and network settings"
- **Paths**: `*/pushConfig.plist`
- **Category**: "Network"

### Artifact 3: Wickr Analytics
- **Name**: "Wickr - Usage Analytics"
- **Description**: "App usage patterns, crash reports, and user behavior analytics"
- **Paths**: `*/com.bugsnag.Bugsnag/com.mywickr.wickr/v1/*`
- **Category**: "Application Usage"

### Artifact 4: Wickr Container Metadata
- **Name**: "Wickr - Container Information"
- **Description**: "App installation metadata and container relationships"
- **Paths**: `*/.com.apple.mobile_container_manager.metadata.plist`
- **Category**: "Application Information"

## 9. Forensic Investigation Value

### What Can Be Determined
1. **App Installation**: Installation date, version, build information
2. **Usage Patterns**: Launch times, session duration, feature usage
3. **Network Configuration**: Server endpoints, communication infrastructure
4. **Device Information**: Hardware specs, timezone, OS version
5. **Feature Usage**: Which Wickr features were enabled/used
6. **Crash Events**: App stability, error conditions

### What Cannot Be Determined
1. **Message Content**: All messages are encrypted and ephemeral
2. **Contact Lists**: No persistent contact storage
3. **Call Records**: No traditional call logs
4. **Media Content**: No cached images, videos, or files
5. **Communication Metadata**: No sender/receiver information

## 10. Conclusion

While Wickr's security-by-design approach means that message content and traditional communication artifacts are not available, significant forensic value exists in configuration files, usage analytics, and network configuration data. The recommended iLEAPP artifacts will provide investigators with:

- User behavior patterns and app usage
- Network infrastructure and communication endpoints
- Device and application configuration information
- Timeline of app usage and state changes

These artifacts, while not providing message content, offer valuable investigative leads and contextual information about Wickr usage on the device.

---

**Analysis Date**: 2025-07-17  
**Analyst**: iLEAPP Artifact Development  
**Wickr Version Analyzed**: 6.4.2 (Build: 600400200001)  
**iOS Version**: 17.0+ (based on app requirements)