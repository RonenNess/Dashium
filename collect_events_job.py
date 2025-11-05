"""
Implement the job that collects events from data collectors.
Author: Ronen Ness.
Created: 2025.
"""
from typing import List, Optional
from data_collector import DataCollector
from db import DatabaseManager
import timer
import logger
import config

log = logger.get_logger("collect_events")

# set by the engine
db: DatabaseManager = None # type: ignore
data_collectors: List[DataCollector] = None # type: ignore


def get_data_collector_status(module: str, unique_id: str = "") -> Optional[dict]:
    """Get the status of a data collector module."""
    for data_collector in data_collectors:
        if data_collector.module_name == module and data_collector.unique_id == unique_id:
            return data_collector.get_status()

    log.warning(f"Data collector not found for module: {module}, unique_id: {unique_id}")
    return None


# function to collect data from all collectors
def collect_data():
    """Run data collection task."""

    log.debug(f"Start events collection job..")

    # iterate over data collectors and collect data
    for data_collector in data_collectors:

        # skip if not time to run yet
        if not data_collector.need_to_run():
            continue
        
        # collect data
        results = data_collector.collect()
        log.info(f"Events collected from {data_collector.module_name}: {len(results)}")
        
        # validate and filter results
        valid_results = []
        for result in results:
            if 'name' not in result:
                log.warning(f"Skipping invalid event collected from {data_collector.module_name}: missing 'name' key.")
                continue
            valid_results.append(result)
        
        # bulk insert all valid events for this collector
        if valid_results:
            success = db.insert_events_bulk(valid_results)
            if not success:
                log.error(f"Failed to insert {len(valid_results)} events from {data_collector.module_name}")
            else:
                log.debug(f"Successfully bulk inserted {len(valid_results)} events from {data_collector.module_name}")

    log.debug(f"Finished events collection job.")


# register the data collection task to run periodically
timer.register_timer(collect_data, config.COLLECT_EVENTS_TASK_INTERVAL_MINUTES)
