"""
Template file to define a new data collector.
"""
from typing import Dict, List, Any
from datetime import datetime

# if you set this to a meaningful string, it will appear as error on the admin panel.
error_message = None


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

    # create event to return
    event = {
        "name": f"example_event",                                   # event name
        "value": 25,                                                # set value based on last value with some random variation
        "tag": "type_a",                                            # example optional tag. you don't have to set tags
        "timestamp": datetime.now()                                 # not mandatory, if None, current time will be used
    }
    return [event]


def get_retention_rules(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get retention rules for the data collector.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary for the data collector
        
    Returns:
        List[Dict[str, Any]]: List of retention rule dictionaries
    """
    # example: keep events for 7 days
    rules = [
        {
            "event_name": "example_event",  # name of the event type to apply the rule to
            "tag": "type_a",                # only delete events with this tag value
            "max_age_days": 7               # maximum age in days to keep the event
        }
    ]
    return rules