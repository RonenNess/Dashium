"""
Define a data collector instance.
Data collectors are custom modules that the host application implement to load different metric values into the database.
Author: Ronen Ness.
Created: 2025.
"""
import sys
import os
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import config
import logger
import math

from persistent_state import PersistentState

log = logger.get_logger("data_collector")

class DataCollector:
    """
    Dynamically load and interface with a data source module.
    """

    def __init__(self, collector_script_name: str, interval_in_minutes: int, collector_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the data source by loading the specified collector script.
        
        Args:
            collector_script_name (str): Name of the data collector script (without .py extension)
            interval_in_minutes (int): Interval in minutes to run the data collector
            collector_config (Optional[Dict[str, Any]]): Optional configuration dictionary for the data collector
            
        Returns:
            None
        """
        # store collector module name
        self.module_name = collector_script_name

        # load the collector module
        self.module = None
        for search_path in [config.APP_DIR, config.ENGINE_DIR]:
            path = Path(os.path.join(search_path, "data_collectors", collector_script_name + ".py"))
            if os.path.exists(path):
                spec = importlib.util.spec_from_file_location(path.stem, path)
                module = importlib.util.module_from_spec(spec) # type: ignore
                sys.modules[path.stem] = module # type: ignore
                spec.loader.exec_module(module) # type: ignore
                self.module = module

        # not found?
        if not self.module:
            raise FileNotFoundError(f"Could not locate data collector: {collector_script_name}.")

        # init data collector
        try:
            self.module.init()  # type: ignore
        except Exception as e:
            log.error(f"Data collector {collector_script_name} has no init() function or it failed: {e}")
            raise e

        # set other properties
        self.interval_in_minutes = interval_in_minutes
        self.config = collector_config or {}
        self.last_execution_time = datetime.now()
        self.runs_count = 0
        self.errors_count = 0
        self.collected_events = 0
        self.avg_execution_time_ms = 0.0
        
        # create persistent state object
        self._persistent_state_path = str(config.DATA_DIR / self.config.get('persistent_state_file_name', f'{self.module_name}_state.json'))
        self.persistent_state = PersistentState()
        self.persistent_state.load(self._persistent_state_path, False)


    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the data source.
        
        Returns:
            Dict[str, Any]: Status information including execution time, error count, etc.
        """
        return {
            "last_execution_time": self.last_execution_time.strftime("%Y-%m-%d %H:%M:%S"),
            "errors_count": self.errors_count,
            "collected_events": self.collected_events,
            "runs_count": self.runs_count,
            "error_message": getattr(self.module, 'error_message', None) or '',
            "avg_execution_time_ms": math.ceil(self.avg_execution_time_ms)
        }
    

    def need_to_run(self) -> bool:
        """
        Check if the data source needs to run based on its interval.
        
        Returns:
            bool: True if the collector should run now, False otherwise
        """
        # special case - first run and configured to run on server start
        if self.runs_count == 0 and self.config.get("collect_when_server_starts", False):
            return True
        
        # check if should run based on interval
        return (datetime.now() - self.last_execution_time).total_seconds() / 60 >= self.interval_in_minutes


    def collect(self) -> List[Any]:
        """
        Invoke the collect function from the data source module.
        
        Returns:
            List[Any]: List of Event instances collected by the data source
        """
        try:
            # update runs count and last execution time
            self.runs_count += 1
            prev_execution_time = self.last_execution_time
            self.last_execution_time = datetime.now()

            # collect data
            ret = self.module.collect(self.config, self.persistent_state, prev_execution_time) # type: ignore

            # save state
            self.persistent_state.save(self._persistent_state_path, True)

            # update average execution time
            curr_execution_time = (datetime.now() - self.last_execution_time).total_seconds() * 1000
            self.avg_execution_time_ms = (self.avg_execution_time_ms * (self.runs_count - 1) + curr_execution_time) / self.runs_count

            # update collected events count
            self.collected_events += len(ret)
            return ret
        
        except Exception as e:
            self.errors_count += 1
            log.error(f"Error collecting data from {self.module_name}: {e}")
            raise e

    def get_retention_rules(self) -> List[Any]:
        """
        Invoke the get_retention_rules function from the data source module.
        
        Returns:
            List[Any]: List of retention rules for the data source
        """
        return self.module.get_retention_rules(self.config) # type: ignore