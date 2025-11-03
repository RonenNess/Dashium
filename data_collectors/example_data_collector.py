"""
This is an example data collector module that returns random events.
To implement a data collector of your own, you must implement two functions: collect(config: dict) and get_retention_rules(config: dict).
View the functions below to see the expected return values.
"""
from typing import Dict, List, Any
from datetime import datetime
import random


def init():
    """Initialize the data collector."""
    pass


last_val = 50


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

    # generate some random events
    events = []
    global last_val

    # create event to return
    event = {
        "name": f"example_event",                                   # event name
        "value": last_val,                                          # set value based on last value with some random variation
        "tag": "type_a" if random.randint(1, 10) < 5 else "type_b", # random tag
        "timestamp": datetime.now()                                 # not mandatory, if None, current time will be used
    }
    events.append(event)

    # update last_val for next iteration
    last_val += random.randint(-5, 5)
    if last_val < 0:
        last_val = 0
    if last_val > 100:
        last_val = 100

    return events


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
            "tag": "type_a",                # only delete events of type a
            "max_age_days": 7               # maximum age in days to keep the event
        },
        {
            "event_name": "example_event",  # name of the event type to apply the rule to
            "tag": "type_b",                # only delete events of type b
            "max_age_days": 14              # maximum age in days to keep the event
        }
    ]
    return rules