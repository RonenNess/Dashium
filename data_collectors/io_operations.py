"""
Collect data about io operations per second.
"""
from typing import Dict, List, Any
from datetime import datetime

error_message = None

try:
    import psutil
except ModuleNotFoundError:
    error_message = "psutil module must be installed to use io operations collector!"
    psutil = None


_last_values = None # type: ignore


def init():
    """Initialize the data collector."""
    global _last_values
    if psutil is not None:
        _last_values = psutil.disk_io_counters()


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
    io1 = _last_values
    io2 = psutil.disk_io_counters()
    
    # Calculate per-second rates
    reads_per_sec = (io2.read_count - io1.read_count) / interval # type: ignore
    writes_per_sec = (io2.write_count - io1.write_count) / interval # type: ignore
    read_bytes_per_sec = (io2.read_bytes - io1.read_bytes) / interval # type: ignore
    write_bytes_per_sec = (io2.write_bytes - io1.write_bytes) / interval # type: ignore
    
    # Update last values and time
    _last_values = io2

    return [{
        "name": "io_operations_read_count_per_sec",
        "value": int(reads_per_sec)
    },
    {
        "name": "io_operations_write_count_per_sec",
        "value": int(writes_per_sec)
    },
    {
        "name": "io_operations_read_bytes_per_sec",
        "value": int(read_bytes_per_sec)
    },
    {
        "name": "io_operations_write_bytes_per_sec",
        "value": int(write_bytes_per_sec)
    }]


def get_retention_rules(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get retention rules for the data collector.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary for the data collector
        
    Returns:
        List[Dict[str, Any]): List of retention rule dictionaries
    """
    rules = [
        {
            "event_name": "io_operations_read_count_per_sec",
            "max_age_days": config.get('retention_days', 7)
        },
        {
            "event_name": "io_operations_write_count_per_sec",
            "max_age_days": config.get('retention_days', 7)
        },
        {
            "event_name": "io_operations_read_bytes_per_sec",
            "max_age_days": config.get('retention_days', 7)
        },
        {
            "event_name": "io_operations_write_bytes_per_sec",
            "max_age_days": config.get('retention_days', 7)
        }
    ]
    return rules