"""
iLEAPP Aggregation Engine

This module provides a centralized system for collecting and aggregating statistics
from various artifacts during the parsing process. It allows artifacts to report
their findings to a central dashboard system.

Usage:
    from scripts.aggregation_engine import AggregationEngine
    
    # Report messaging statistics from an artifact
    AggregationEngine.report_messaging_count("WhatsApp", 1308)
    
    # Get all collected statistics
    stats = AggregationEngine.get_dashboard_data()
"""

import json
from typing import Dict, List, Any
from collections import defaultdict, OrderedDict


class AggregationEngine:
    """
    Singleton class for collecting and aggregating artifact statistics.
    This engine runs post-processing to generate dashboard data.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AggregationEngine, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.reset()
            self._initialized = True
    
    def reset(self):
        """Reset all collected statistics - useful for testing and new runs."""
        self._messaging_apps = defaultdict(int)
        self._social_media_apps = defaultdict(int)
        self._location_sources = defaultdict(int)
        self._device_info = {}
        self._timeline_events = []
        self._artifact_counts = defaultdict(int)
        self._processing_errors = []
    
    @classmethod
    def report_messaging_count(cls, app_name: str, message_count: int):
        """
        Report the number of messages found for a messaging app.
        
        Args:
            app_name: Name of the messaging application (e.g., "WhatsApp", "Telegram")
            message_count: Total number of messages found
        """
        instance = cls()
        instance._messaging_apps[app_name] += message_count
    
    @classmethod
    def report_social_media_count(cls, app_name: str, activity_count: int):
        """
        Report social media activity count.
        
        Args:
            app_name: Name of the social media app
            activity_count: Number of activities/posts/interactions found
        """
        instance = cls()
        instance._social_media_apps[app_name] += activity_count
    
    @classmethod
    def report_location_data(cls, source: str, location_count: int):
        """
        Report location data points.
        
        Args:
            source: Source of location data (e.g., "Maps", "Photos", "Weather")
            location_count: Number of location data points found
        """
        instance = cls()
        instance._location_sources[source] += location_count
    
    @classmethod
    def report_artifact_processed(cls, artifact_name: str, record_count: int):
        """
        Report that an artifact has been processed with its record count.
        
        Args:
            artifact_name: Name of the processed artifact
            record_count: Number of records found in the artifact
        """
        instance = cls()
        instance._artifact_counts[artifact_name] = record_count
    
    @classmethod
    def report_device_info(cls, key: str, value: Any):
        """
        Report device information.
        
        Args:
            key: Information key (e.g., "ios_version", "device_name")
            value: Information value
        """
        instance = cls()
        instance._device_info[key] = value
    
    @classmethod
    def report_processing_error(cls, artifact_name: str, error_msg: str):
        """
        Report processing errors for dashboard visibility.
        
        Args:
            artifact_name: Name of the artifact that had an error
            error_msg: Error message description
        """
        instance = cls()
        instance._processing_errors.append({
            "artifact": artifact_name,
            "error": error_msg
        })
    
    @classmethod
    def get_top_messaging_apps(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the top messaging apps by message count.
        
        Args:
            limit: Maximum number of apps to return
            
        Returns:
            List of dictionaries containing app names and message counts
        """
        instance = cls()
        sorted_apps = sorted(instance._messaging_apps.items(), 
                           key=lambda x: x[1], reverse=True)
        
        return [{"app": app, "count": count} for app, count in sorted_apps[:limit]]
    
    @classmethod
    def get_dashboard_data(cls) -> Dict[str, Any]:
        """
        Get all collected data for dashboard generation.
        
        Returns:
            Dictionary containing all aggregated statistics
        """
        instance = cls()
        
        # Calculate totals
        total_messages = sum(instance._messaging_apps.values())
        total_social_activities = sum(instance._social_media_apps.values())
        total_location_points = sum(instance._location_sources.values())
        total_artifacts_processed = len([count for count in instance._artifact_counts.values() if count > 0])
        
        # Sort messaging apps by count (descending)
        top_messaging_apps = sorted(instance._messaging_apps.items(), 
                                  key=lambda x: x[1], reverse=True)
        
        # Sort social media apps by count (descending)
        top_social_apps = sorted(instance._social_media_apps.items(), 
                               key=lambda x: x[1], reverse=True)
        
        # Sort location sources by count (descending)
        top_location_sources = sorted(instance._location_sources.items(), 
                                    key=lambda x: x[1], reverse=True)
        
        return {
            "summary": {
                "total_messages": total_messages,
                "total_social_activities": total_social_activities,
                "total_location_points": total_location_points,
                "total_artifacts_processed": total_artifacts_processed,
                "processing_errors": len(instance._processing_errors)
            },
            "messaging_apps": {
                "apps": top_messaging_apps,
                "total": total_messages
            },
            "social_media_apps": {
                "apps": top_social_apps,
                "total": total_social_activities
            },
            "location_sources": {
                "sources": top_location_sources,
                "total": total_location_points
            },
            "device_info": dict(instance._device_info),
            "artifact_counts": dict(instance._artifact_counts),
            "errors": instance._processing_errors
        }
    
    @classmethod
    def get_messaging_chart_data(cls) -> Dict[str, Any]:
        """
        Get messaging data formatted for chart generation.
        
        Returns:
            Dictionary with labels and data arrays for charting
        """
        instance = cls()
        sorted_apps = sorted(instance._messaging_apps.items(), 
                           key=lambda x: x[1], reverse=True)
        
        if not sorted_apps:
            return {"labels": [], "data": [], "total": 0}
        
        # Limit to top 10 for readability
        top_apps = sorted_apps[:10]
        
        return {
            "labels": [app for app, _ in top_apps],
            "data": [count for _, count in top_apps],
            "total": sum(instance._messaging_apps.values()),
            "apps_count": len(instance._messaging_apps)
        }
    
    @classmethod
    def clear_all_data(cls):
        """Clear all collected data - useful for testing."""
        instance = cls()
        instance.reset()
    
    @classmethod
    def export_data_to_json(cls, file_path: str):
        """
        Export all aggregated data to a JSON file.
        
        Args:
            file_path: Path where to save the JSON file
        """
        instance = cls()
        data = instance.get_dashboard_data()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def has_data(cls) -> bool:
        """
        Check if any data has been collected.
        
        Returns:
            True if any statistics have been reported
        """
        instance = cls()
        return (bool(instance._messaging_apps) or 
                bool(instance._social_media_apps) or 
                bool(instance._location_sources) or 
                bool(instance._device_info) or
                bool(instance._artifact_counts))


# Convenience functions for common use cases
def report_messaging_stats(app_name: str, message_count: int):
    """Convenience function to report messaging statistics."""
    AggregationEngine.report_messaging_count(app_name, message_count)

def report_social_stats(app_name: str, activity_count: int):
    """Convenience function to report social media statistics."""
    AggregationEngine.report_social_media_count(app_name, activity_count)

def report_location_stats(source: str, location_count: int):
    """Convenience function to report location statistics."""
    AggregationEngine.report_location_data(source, location_count)

def get_dashboard_summary():
    """Convenience function to get dashboard summary data."""
    return AggregationEngine.get_dashboard_data()