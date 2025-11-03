"""
Collect data about disk usage.
"""
from typing import Dict, List, Any
from datetime import datetime

error_message = None

try:
    import psutil
except ModuleNotFoundError:
    error_message = "psutil module must be installed to use disk usage collector!"
    psutil = None


def init():
    """Initialize the data collector."""
    pass


def collect(config: Dict[str, Any], persistent_state: object, last_execution_time: datetime) -> List[Dict[str, Any]]:
    """
    Collect data from the data source.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary for the data collector
        persistent_state (object): Persistent state object to store collector state between runs and server executions
        last_execution_time (datetime): The last time the collector was executed

    Returns:
        List[Dict[str, Any]]: List of event dictionaries collected from the data source
    """
    if psutil is None:
        return []
    
    usage = psutil.disk_usage(config.get('path', '/'))
    return [{
        "name": "disk_usage_percent",
        "value": int(usage.percent)
    },
    {
        "name": "disk_usage_used_mb",
        "value": int(usage.used / (1024 ** 2))
    },
    {
        "name": "disk_usage_free_mb",
        "value": int(usage.free / (1024 ** 2))
    }]


def get_retention_rules(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get retention rules for the data collector.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary for the data collector
        
    Returns:
        List[Dict[str, Any]]: List of retention rule dictionaries
    """
    rules = [
        {
            "event_name": "disk_usage_percent",
            "max_age_days": config.get('retention_days', 14)
        },
        {
            "event_name": "disk_usage_used_mb",
            "max_age_days": config.get('retention_days', 14)
        },
        {
            "event_name": "disk_usage_free_mb",
            "max_age_days": config.get('retention_days', 14)
        }
    ]
    return rules
