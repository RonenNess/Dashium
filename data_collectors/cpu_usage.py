"""
Collect data about CPU usage.
"""
from typing import Dict, List, Any
from datetime import datetime

error_message = None

try:
    import psutil
except ModuleNotFoundError:
    error_message = "psutil module must be installed to use cpu usage collector!"
    psutil = None


def init():
    """Initialize the data collector."""
    if psutil is not None:
        psutil.cpu_percent()


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
    
    cpu_percent = psutil.cpu_percent()
    return [{
        "name": "cpu_usage",
        "value": int(cpu_percent)
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
            "event_name": "cpu_usage",
            "max_age_days": config.get('retention_days', 7)
        }
    ]
    return rules