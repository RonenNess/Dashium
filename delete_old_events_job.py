"""
A job to delete old events from the database based on retention policies.
Author: Ronen Ness.
Created: 2025.
"""
from typing import List
from data_collector import DataCollector
from db import DatabaseManager
import timer
import logger
import config

log = logger.get_logger("delete_old_events")

# set by the engine
db: DatabaseManager = None # type: ignore
data_collectors: List[DataCollector] = None # type: ignore

# function to delete old events
def delete_old_events():
    """Delete old events from the database."""
    log.debug(f"Start old events cleanup job..")

    # iterate over data collectors and collect data
    for data_collector in data_collectors:

        total_deleted_count = 0
        rules = data_collector.get_retention_rules()
        for rule in rules:

            # validate rule
            if 'event_name' not in rule:
                log.error(f"Skipping invalid retention rule from {data_collector.module_name}: missing 'name' key.")
                return 
            
            if 'max_age_days' not in rule:
                log.error(f"Skipping invalid retention rule from {data_collector.module_name}: missing 'max_age_days' key.")
                return

            # delete old events
            event_name = rule["event_name"]
            age_days = rule["max_age_days"]
            tag = rule.get("tag")
            deleted_count = db.delete_old_events(event_name, tag, age_days)
            log.info(f"Deleted {deleted_count} old events of type '{event_name}' from the database.")
            total_deleted_count += deleted_count
        
        data_collector.add_deleted_events_count(total_deleted_count)

    log.debug(f"Finished old events cleanup job!")

# register the old events deletion task to run periodically
timer.register_timer(delete_old_events, config.DELETE_OLD_EVENTS_TASK_INTERVAL_MINUTES * 60)
