"""
Collect data about network usage.
"""
from typing import Dict, List, Any
from datetime import datetime

error_message = None

try:
    import psutil
except ModuleNotFoundError:
    error_message = "psutil module must be installed to use network usage collector!"
    psutil = None


_last_values = None # type: ignore


def init():
    """Initialize the data collector."""
    global _last_values
    if psutil is not None:
        _last_values = psutil.net_io_counters()


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
    
    global _last_values

    # Get measurement interval
    interval = (datetime.now() - last_execution_time).total_seconds()
    
    # Take first measurement
    net1 = _last_values
    net2 = psutil.net_io_counters()
    
    # Calculate bytes per second
    bytes_sent_per_sec = (net2.bytes_sent - net1.bytes_sent) / interval # type: ignore
    bytes_recv_per_sec = (net2.bytes_recv - net1.bytes_recv) / interval # type: ignore
    
    # Update last values and time
    _last_values = net2

    return [{
        "name": "network_usage_bytes_sent_per_sec",
        "value": int(bytes_sent_per_sec)
    },
    {
        "name": "network_usage_bytes_recv_per_sec", 
        "value": int(bytes_recv_per_sec)
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
            "event_name": "network_usage_bytes_sent_per_sec",
            "max_age_days": config.get('retention_days', 7)
        },
        {
            "event_name": "network_usage_bytes_recv_per_sec",
            "max_age_days": config.get('retention_days', 7)
        }
    ]
    return rules