"""
Log File Data Collector
Parses log files and extracts log entries with timestamps, severity levels, and messages.
Uses persistent state to track the last read timestamp to avoid re-reading processed lines.
Author: Ronen Ness.
Created: 2025.
"""
import re
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import logger
from persistent_state import PersistentState

log = logger.get_logger(__name__)

error_message = None

# Example log patterns that can be used in configuration:
# Pattern 1: "2025-10-27 14:30:25 ERROR Message here"
# r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+(\w+)\s+(.+)$'
# 
# Pattern 2: "[2025-10-27 14:30:25] ERROR: Message here"
# r'^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\]\s+(\w+):\s*(.+)$'
# 
# Pattern 3: "Oct 27 14:30:25 ERROR Message here"
# r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.+)$'
# 
# Pattern 4: "2025/10/27 14:30:25 [ERROR] Message here"
# r'^(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+\[(\w+)\]\s+(.+)$'
# 
# Pattern 5: Simple format "TIMESTAMP LEVEL MESSAGE"
# r'^(\S+\s+\S+)\s+(\w+)\s+(.+)$'

# Example timestamp formats that can be used in configuration:
# '%Y-%m-%d %H:%M:%S'
# '%Y-%m-%d %H:%M:%S.%f'
# '%b %d %H:%M:%S'
# '%Y/%m/%d %H:%M:%S'
# '%Y/%m/%d %H:%M:%S.%f'


def init():
    """Initialize the log file data collector."""
    pass


def collect(config: Dict[str, Any], persistent_state: PersistentState, last_execution_time: datetime) -> List[Dict[str, Any]]:
    """
    Collect new log entries from the configured log file.
    
    Args:
        config (Dict[str, Any]): Configuration containing 'log_file_path', 'log_pattern', and 'timestamp_format'
        persistent_state (object): Persistent state object for tracking last read position
        last_execution_time (datetime): Last time this collector was executed
        
    Returns:
        List[Dict[str, Any]]: List of events representing new log entries
    """
    global error_message
    events = []
    
    try:
        # Get configuration
        log_file_path = config.get('log_file_path')
        if not log_file_path:
            error_message = "log_file_path not specified in collector configuration"
            return events
        
        timestamp_format = config.get('timestamp_format')
        log_pattern = config.get('log_pattern')
        
        # Validate required configuration
        if not log_pattern:
            error_message = "log_pattern not specified in collector configuration"
            return events
        
        if not timestamp_format:
            error_message = "timestamp_format not specified in collector configuration"
            return events
        
        # Check if log file exists
        if not os.path.exists(log_file_path):
            error_message = f"Log file not found: {log_file_path}"
            return events
        
        # Get state key for this log file
        state_key = f"log_collector_{os.path.basename(log_file_path)}"
        
        # Get last processed timestamp from persistent state
        last_timestamp = _get_last_timestamp(persistent_state, state_key)
        log.debug(f"Last processed timestamp for {log_file_path}: {last_timestamp}")
        
        # Read and parse log file
        new_lines = _read_new_log_lines(log_file_path, last_timestamp, timestamp_format, log_pattern)
        
        # Process each new line
        latest_timestamp = last_timestamp
        for line_data in new_lines:
            try:
                event = _create_event_from_log_line(line_data)
                if event:
                    events.append(event)
                    # Track the latest timestamp
                    if line_data['timestamp'] > latest_timestamp:
                        latest_timestamp = line_data['timestamp']
                        
            except Exception as e:
                error_message = f"Failed to process log line: {line_data.get('raw_line', 'N/A')} - {e}"
        
        # Update last processed timestamp
        if latest_timestamp > last_timestamp:
            _save_last_timestamp(persistent_state, state_key, latest_timestamp, log_file_path)
            log.debug(f"Updated last processed timestamp to: {latest_timestamp}")
        
        log.info(f"Collected {len(events)} new log entries from {log_file_path}")
        
        # Set error_message to None after successful collection
        error_message = None
        
    except Exception as e:
        error_message = f"Error collecting log data: {e}"
    
    return events


def get_retention_rules(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Return retention rules for log message events.
    
    Args:
        config (Dict[str, Any]): Collector configuration
        
    Returns:
        List[Dict[str, Any]]: List of retention rules
    """
    return [
        {
            'event_name': 'log_message',
            'retention_days': config.get('retention_days', 30)
        }
    ]


def _get_last_timestamp(persistent_state: PersistentState, state_key: str) -> datetime:
    """
    Get the last processed timestamp from persistent state.
    
    Args:
        persistent_state (object): Persistent state object
        state_key (str): State key for this log file
        
    Returns:
        datetime: Last processed timestamp, or epoch if not found
    """
    global error_message
    try:
        state_data = persistent_state.get(state_key)
        if state_data and 'last_timestamp' in state_data:
            return datetime.fromisoformat(state_data['last_timestamp'])
    except Exception as e:
        error_message = f"Failed to get last timestamp from state: {e}"
    
    # Return epoch time if no previous state
    return datetime(1970, 1, 1)


def _save_last_timestamp(persistent_state: PersistentState, state_key: str, timestamp: datetime, log_file_path: str) -> None:
    """
    Save the last processed timestamp to persistent state.
    
    Args:
        persistent_state (object): Persistent state object
        state_key (str): State key for this log file
        timestamp (datetime): Timestamp to save
        log_file_path (str): Path to the log file
    """
    global error_message
    try:
        state_data = {
            'last_timestamp': timestamp.isoformat(),
            'log_file_path': log_file_path
        }
        persistent_state.set(state_key, state_data)
    except Exception as e:
        error_message = f"Failed to save last timestamp to state: {e}"


def _read_new_log_lines(log_file_path: str, last_timestamp: datetime, 
                       timestamp_format: str, 
                       log_pattern: str) -> List[Dict[str, Any]]:
    """
    Read new log lines from the file that are newer than the last timestamp.
    
    Args:
        log_file_path (str): Path to the log file
        last_timestamp (datetime): Only process lines newer than this
        timestamp_format (str): Timestamp format from configuration
        log_pattern (str): Log parsing pattern from configuration
        
    Returns:
        List[Dict[str, Any]]: List of parsed log line data
    """
    global error_message
    new_lines = []
    
    try:
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Parse the log line
                parsed_line = _parse_log_line(line, line_num, timestamp_format, log_pattern)
                
                if parsed_line and parsed_line['timestamp'] > last_timestamp:
                    new_lines.append(parsed_line)
                    
    except Exception as e:
        error_message = f"Failed to read log file {log_file_path}: {e}"
    
    return new_lines


def _parse_log_line(line: str, line_num: int, 
                   timestamp_format: str, 
                   log_pattern: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single log line to extract timestamp, severity, and message.
    
    Args:
        line (str): Raw log line
        line_num (int): Line number in file
        timestamp_format (str): Timestamp format from configuration
        log_pattern (str): Log parsing pattern from configuration
        
    Returns:
        Optional[Dict[str, Any]]: Parsed line data or None if parsing failed
    """
    # Use the single pattern from config
    match = re.match(log_pattern, line)
    if match:
        try:
            timestamp_str = match.group(1)
            severity = match.group(2).upper()
            message = match.group(3).strip()
            
            # Parse timestamp
            timestamp = _parse_timestamp(timestamp_str, timestamp_format)
            if timestamp:
                return {
                    'timestamp': timestamp,
                    'severity': severity,
                    'message': message,
                    'raw_line': line,
                    'line_number': line_num
                }
            
        except Exception as e:
            log.debug(f"Failed to parse line {line_num} with pattern: {e}")
    
    # If no pattern matched, log a debug message
    log.debug(f"Could not parse log line {line_num}: {line[:100]}...")
    return None


def _parse_timestamp(timestamp_str: str, timestamp_format: str) -> Optional[datetime]:
    """
    Parse timestamp string using various formats.
    
    Args:
        timestamp_str (str): Timestamp string from log
        timestamp_format (str): Timestamp format from configuration
        
    Returns:
        Optional[datetime]: Parsed timestamp or None if parsing failed
    """
    try:
        # Handle special case for syslog format (no year)
        if timestamp_format == '%b %d %H:%M:%S':
            # Add current year to syslog format
            current_year = datetime.now().year
            timestamp_str_with_year = f"{current_year} {timestamp_str}"
            return datetime.strptime(timestamp_str_with_year, f'%Y %b %d %H:%M:%S')
        else:
            return datetime.strptime(timestamp_str, timestamp_format)
            
    except ValueError:
        pass
    
    log.debug(f"Could not parse timestamp: {timestamp_str}")
    return None


def _create_event_from_log_line(line_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create an event dictionary from parsed log line data.
    
    Args:
        line_data (Dict[str, Any]): Parsed log line data
        
    Returns:
        Dict[str, Any]: Event data for the data collection system
    """
    return {
        'name': 'log_message',
        'value': 1,  # Count of log messages
        'timestamp': line_data['timestamp'].isoformat(),
        'tag': line_data['severity'],
        'additional_info': line_data['message']
    }
