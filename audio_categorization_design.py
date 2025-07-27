"""
Audio Categorization System Design
Based on forensic research of iOS audio file patterns and locations

This design document defines the intelligent categorization system for the allUserAudio artifact.
"""

# Audio Type Categories with Forensic Relevance Scoring
AUDIO_CATEGORIES = {
    "USER_CONTENT": {
        "name": "User Content",
        "description": "Audio created or customized by the user",
        "forensic_relevance": "HIGH",
        "patterns": [
            # Custom ringtones 
            "*/Library/Sounds/ringtone_*.mp3",
            "*/Library/Sounds/ringtone_*.m4a", 
            # Voice Memos app audio files
            "*/Containers/Data/Application/*/Documents/*.m4a",
            "*/Containers/Data/Application/*/Documents/*.caf",
            "*/Containers/Data/Application/*/Documents/*.wav",
            "*/Containers/Data/Application/*/Documents/*.mp3",
            # User recordings in other apps
            "*/Documents/Recordings/*",
        ],
        "size_heuristics": {
            "min_size": 50000,  # 50KB+ for substantial user content
            "typical_range": (100000, 10000000)  # 100KB - 10MB
        },
        "context_indicators": [
            "has_database_reference",
            "in_voice_memos_container", 
            "custom_filename",
            "user_created_timestamp"
        ]
    },
    
    "COMMUNICATION_AUDIO": {
        "name": "Communication Audio", 
        "description": "Voice messages, voicemail, call-related audio",
        "forensic_relevance": "HIGH",
        "patterns": [
            # Voicemail
            "*/mobile/Library/Voicemail/*.amr",
            "*/mobile/Library/Voicemail/*/*.amr",
            # WhatsApp voice messages
            "*/Containers/Shared/AppGroup/*/Message/Media/*/*/*.opus",
            "*/Containers/Shared/AppGroup/*/Message/Media/*/*/*.m4a",
            # SMS/iMessage attachments
            "*/mobile/Library/SMS/Attachments/*.m4a",
            "*/mobile/Library/SMS/Attachments/*.caf",
            # Telegram voice messages
            "*/telegram-data/account-*/postbox/media/*/*.ogg",
            # Signal voice messages 
            "*/Library/Application Support/Attachments/*.m4a",
        ],
        "size_heuristics": {
            "min_size": 5000,   # 5KB for short voice messages
            "typical_range": (20000, 5000000)  # 20KB - 5MB
        },
        "context_indicators": [
            "in_messaging_database",
            "has_chat_reference",
            "voicemail_reference",
            "communication_timestamp"
        ]
    },

    "SYSTEM_AUDIO": {
        "name": "System Audio",
        "description": "Device personalization and system sounds", 
        "forensic_relevance": "MEDIUM",
        "patterns": [
            # System notification sounds
            "*/Library/Sounds/*.mp3",
            "*/Library/Sounds/*.caf", 
            "*/Library/Sounds/*.wav",
            # Custom alert tones
            "*/Preferences/*.caf",
            # System audio files
            "*/System/Library/Audio/*",
        ],
        "size_heuristics": {
            "min_size": 1000,   # 1KB minimum
            "typical_range": (5000, 200000)  # 5KB - 200KB
        },
        "context_indicators": [
            "system_preferences_reference",
            "default_system_location",
            "notification_context"
        ]
    },

    "VOICE_COMMANDS": {
        "name": "Voice Commands",
        "description": "Siri triggers, voice training, accessibility audio",
        "forensic_relevance": "MEDIUM", 
        "patterns": [
            # Siri voice triggers
            "*/Library/VoiceTrigger/SAT/com.apple.siri/*/*/td/audio/*.wav",
            "*/Library/VoiceTrigger/SAT/com.apple.siri/*/*/tdti/audio/*.wav",
            # Voice training data
            "*/Library/VoiceTrigger/*/*.wav",
            # Accessibility voice
            "*/Library/Speech/*",
        ],
        "size_heuristics": {
            "min_size": 10000,  # 10KB minimum for voice samples
            "typical_range": (50000, 100000)  # 50-100KB typical for Siri samples
        },
        "context_indicators": [
            "siri_trigger_path",
            "voice_training_context",
            "accessibility_reference"
        ]
    },

    "APP_ASSETS": {
        "name": "App Assets",
        "description": "Built-in app sounds, UI feedback, game audio",
        "forensic_relevance": "LOW",
        "patterns": [
            # App bundle audio
            "*/containers/Bundle/Application/*/*.app/*.mp3",
            "*/containers/Bundle/Application/*/*.app/*.caf", 
            "*/containers/Bundle/Application/*/*.app/*.wav",
            "*/containers/Bundle/Application/*/*.app/*.m4a",
            # App frameworks
            "*/containers/Bundle/Application/*/*.app/Frameworks/*/*.mp3",
            "*/containers/Bundle/Application/*/*.app/Frameworks/*/*.m4a",
            # App resource bundles
            "*/containers/Bundle/Application/*/*.app/*.bundle/*.mp3",
            "*/containers/Bundle/Application/*/*.app/*.bundle/*.caf",
        ],
        "size_heuristics": {
            "min_size": 500,    # 500 bytes minimum
            "typical_range": (1000, 50000)  # 1KB - 50KB for app sounds
        },
        "context_indicators": [
            "app_bundle_path",
            "ui_sound_name",
            "framework_reference",
            "resource_bundle_location"
        ]
    },

    "UNKNOWN": {
        "name": "Unknown Audio",
        "description": "Audio files that don't match classification patterns",
        "forensic_relevance": "MEDIUM",  # Default to medium for safety
        "patterns": [],  # Catch-all category
        "size_heuristics": {
            "min_size": 0,
            "typical_range": (0, float('inf'))
        },
        "context_indicators": []
    }
}

# Path Pattern Matching Priority (higher number = higher priority)
PATTERN_PRIORITIES = {
    "USER_CONTENT": 90,
    "COMMUNICATION_AUDIO": 85, 
    "VOICE_COMMANDS": 70,
    "SYSTEM_AUDIO": 60,
    "APP_ASSETS": 40,
    "UNKNOWN": 10
}

# File Size Categories for Additional Context
SIZE_CATEGORIES = {
    "VERY_SMALL": (0, 5000),      # 0-5KB - likely UI sounds
    "SMALL": (5001, 50000),       # 5-50KB - short audio clips
    "MEDIUM": (50001, 500000),    # 50-500KB - voice messages, short recordings
    "LARGE": (500001, 5000000),   # 500KB-5MB - longer recordings
    "VERY_LARGE": (5000001, float('inf'))  # 5MB+ - music, long recordings
}

# Forensic Relevance Scoring
FORENSIC_SCORES = {
    "HIGH": 3,    # Direct evidence value - user content, communications
    "MEDIUM": 2,  # Indirect evidence - system personalization, voice commands  
    "LOW": 1      # Limited evidence - app assets, UI sounds
}

def classify_audio_file(file_path, file_size, database_context=None):
    """
    Classify an audio file based on path patterns, size, and context.
    
    Args:
        file_path (str): Full path to the audio file
        file_size (int): Size of the file in bytes
        database_context (dict): Optional context from database references
        
    Returns:
        dict: Classification result with category, confidence, and metadata
    """
    
    # Implementation will use pattern matching, size analysis, and context
    # to determine the most likely category with confidence scoring
    
    pass  # To be implemented in the main artifact

# Database Context Patterns for Enhanced Classification
DATABASE_PATTERNS = {
    "VOICE_MEMOS": {
        "database_name": "Recordings.sqlite",
        "table_indicators": ["ZRECORDING", "ZFOLDER"],
        "category_boost": "USER_CONTENT"
    },
    "SMS_IMESSAGE": {
        "database_name": "sms.db", 
        "table_indicators": ["message", "attachment"],
        "category_boost": "COMMUNICATION_AUDIO"
    },
    "WHATSAPP": {
        "database_name": "ChatStorage.sqlite",
        "table_indicators": ["ZWAMESSAGE", "ZWAMEDIAITEM"],
        "category_boost": "COMMUNICATION_AUDIO"
    },
    "VOICEMAIL": {
        "database_name": "voicemail.db",
        "table_indicators": ["voicemail"],
        "category_boost": "COMMUNICATION_AUDIO"
    }
}

# Enhanced Output Schema for Forensic Reports
ENHANCED_OUTPUT_SCHEMA = [
    "Timestamp",
    "Audio Type",           # USER_CONTENT, COMMUNICATION_AUDIO, etc.
    "Functional Category",  # Ringtone, Voice Message, App Sound, etc.
    "Forensic Relevance",   # HIGH, MEDIUM, LOW
    "User Relevance Score", # 1-3 scoring
    "File Path",
    "File Size",
    "Duration", 
    "Source App/System",
    "Database Reference",
    "Classification Confidence",
    "Custom/Default Indicator",
    "Participant Info",     # For communication audio
    "Source File"
]