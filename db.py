"""
Wrap a simple sqlite3 database for storing and retrieving analytics events.
Author: Ronen Ness.
Created: 2025.
"""
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union, Sequence
import logger

log = logger.get_logger(__name__)


class Event:
    """
    Represents a single analytics event.
    """

    def __init__(self, name: str, value: int = 0, tag: Optional[str] = None, additional_info: Optional[str] = None, timestamp: Optional[datetime] = None) -> None:
        """
        Initialize an Event object.
        
        Args:
            name (str): Name of the event
            value (int): Value associated with the event (default: 0)
            tag (Optional[str]): Optional tag for categorizing the event (default: None)
            timestamp (Optional[datetime]): Timestamp of the event (default: current time)
            
        Returns:
            None
        """
        self.name = name
        self.value = value
        self.tag = tag
        self.additional_info = None
        self.timestamp = timestamp or datetime.now()


class DatabaseManager:
    """
    Manage the SQLite database for storing and retrieving analytics counters.
    """

    def __init__(self, db_path: str = "analytics.db"):
        """
        Initialize the database manager with the specified database path.
        
        Args:
            db_path (str): Path to the SQLite database file
        """
        self.db_path = db_path
        self._local = threading.local()

    def connect(self) -> None:
        """
        Initialize the database connection.
        
        Returns:
            None
        """
        log.info(f"Connecting to database {self.db_path} on thread {threading.get_ident()}.")
        self._local.conn = sqlite3.connect(self.db_path)
        self._local.conn.row_factory = sqlite3.Row
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Create and return a database connection.
        
        Returns:
            sqlite3.Connection: Database connection object
        """
        if not hasattr(self._local, "conn"):
            self.connect()
        return self._local.conn


    def init_database(self) -> None:
        """
        Initialize the database and create the Counters table if it doesn't exist.
        
        Returns:
            None
        """
        with self.get_connection() as conn:

            log.info(f"Initializing database schema in {self.db_path}.")

            cursor = conn.cursor()
            
            # Create Counters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value INTEGER NOT NULL DEFAULT 0,
                    tag TEXT DEFAULT NULL,
                    additional_info TEXT DEFAULT NULL,
                    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index on name, tag and timestamp for faster lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_name ON Events(name)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_tag ON Events(tag)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_timestamp ON Events(timestamp)
            ''')

            conn.commit()


    def insert_event(self, data: Event) -> bool:
        """
        Insert a new event.
        
        Args:
            data (Event): Event object containing name, value, tag, and timestamp
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.insert_event_data(data.name, data.value, data.tag, data.additional_info, data.timestamp)


    def insert_events(self, events: List[Event]) -> bool:
        """
        Insert multiple Event objects in a single database transaction for better performance.

        Args:
            events (List[Event]): List of Event objects to insert.

        Returns:
            bool: True if successful, False otherwise
        """
        return self.insert_events_bulk(events)


    def insert_event_data(self, name: str, value: int, tag: Optional[str] = None, additional_info: Optional[str] = None, timestamp: Optional[datetime] = None) -> bool:
        """
        Insert a new event or update existing one.

        Args:
            name (str): Event name.
            value (int): Event value.
            tag (str): Optional tag to mark this event (we can filter by it later).
            additional_info (str): Optional additional information about the event.
            timestamp (datetime, optional): Timestamp. Defaults to current time.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if timestamp is None:
                    timestamp = datetime.now()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO Events (name, value, tag, additional_info, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, value, tag, additional_info, timestamp))

                conn.commit()
                return True
            
        except sqlite3.Error as e:
            log.error(f"Error inserting event: {e}")
            return False


    def insert_events_bulk(self, events: Sequence[Union[Event, Dict[str, Any]]]) -> bool:
        """
        Insert multiple events in a single database transaction for better performance.

        Args:
            events (List[Union[Event, Dict[str, Any]]]): List of Event objects or dictionaries with event data.
                Dictionary format: {'name': str, 'value': int, 'tag': str, 'additional_info': str, 'timestamp': datetime}
                All fields except 'name' and 'value' are optional.

        Returns:
            bool: True if successful, False otherwise
        """
        if not events:
            return True
            
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Prepare data for bulk insert
                event_data = []
                current_time = datetime.now()
                
                for event in events:
                    if isinstance(event, Event):
                        # Handle Event object
                        event_data.append((
                            event.name,
                            event.value,
                            event.tag,
                            event.additional_info,
                            event.timestamp or current_time
                        ))
                    elif isinstance(event, dict):
                        # Handle dictionary
                        event_data.append((
                            event.get('name'),
                            event.get('value', 0),
                            event.get('tag'),
                            event.get('additional_info'),
                            event.get('timestamp') or current_time
                        ))
                    else:
                        log.warning(f"Skipping invalid event type: {type(event)}")
                        continue
                
                # Bulk insert using executemany
                cursor.executemany('''
                    INSERT OR REPLACE INTO Events (name, value, tag, additional_info, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', event_data)

                conn.commit()
                log.debug(f"Successfully inserted {len(event_data)} events in bulk")
                return True
            
        except sqlite3.Error as e:
            log.error(f"Error inserting events in bulk: {e}")
            return False


    def get_events(self, name: str, tags: Optional[Union[str, List[str]]] = None, max_age_days: int = 0, max_results: int = 0) -> List[Dict[str, Any]]:
        """
        Get all events from the database.

        Args:
            name (str): Event name to filter by (required).
            tag (str | List[str]): If provided, will filter by tag. Can be a single tag or list of tags.
            max_age_days (int): If provided, will only return events younger than this many days.
            max_results (int): If provided, will limit the number of events returned.

        Returns:
            List[Event]: List of Event objects
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build the query dynamically based on filters
                query = 'SELECT name, value, tag, additional_info, timestamp FROM Events WHERE name = ?'
                params: List[Any] = [name]
                
                # Add max_age_days filter if provided
                if max_age_days > 0:
                    cutoff_date = datetime.now() - timedelta(days=max_age_days)
                    query += ' AND timestamp >= ?'
                    params.append(cutoff_date)
                
                # Add tag filter if provided
                if tags is not None:
                    if isinstance(tags, list):
                        if len(tags) == 1:
                            # Single tag in list - simple comparison
                            query += ' AND tag = ?'
                            params.append(tags[0])
                        elif len(tags) > 1:
                            # Multiple tags - use IN clause
                            placeholders = ','.join(['?'] * len(tags))
                            query += f' AND tag IN ({placeholders})'
                            params.extend(tags)
                    else:
                        # Single string tag - simple comparison
                        query += ' AND tag = ?'
                        params.append(tags)
                
                # If limit is provided, order DESC to get most recent first, then reverse
                if max_results > 0:
                    query += ' ORDER BY timestamp DESC LIMIT ?'
                    params.append(max_results)
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    return [dict(row) for row in reversed(rows)] # Reverse to get chronological order (oldest first)
                
                # No limit, just order chronologically
                else:
                    query += ' ORDER BY timestamp ASC'
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]

        except sqlite3.Error as e:
            log.error(f"Error getting all events: {e}")
            return []


    def get_latest_events_by_tag(self, name: str, tags: Optional[Union[str, List[str]]] = None) -> List[Dict[str, Any]]:
        """
        Get the most recent event for each distinct tag value.

        Args:
            name (str): Event name to filter by (required).
            tags (Optional[Union[str, List[str]]]): If provided, will filter by tag. Can be a single tag or list of tags.

        Returns:
            List[Dict[str, Any]]: List of the most recent events, one per unique tag
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query to get the most recent event for each tag
                query = '''
                    SELECT e1.name, e1.value, e1.tag, e1.additional_info, e1.timestamp 
                    FROM Events e1
                    INNER JOIN (
                        SELECT tag, MAX(timestamp) as max_timestamp
                        FROM Events 
                        WHERE name = ?
                '''
                params: List[Any] = [name]
                
                # Add tag filter to subquery if provided
                if tags is not None:
                    if isinstance(tags, list):
                        if len(tags) == 1:
                            query += ' AND tag = ?'
                            params.append(tags[0])
                        elif len(tags) > 1:
                            placeholders = ','.join(['?'] * len(tags))
                            query += f' AND tag IN ({placeholders})'
                            params.extend(tags)
                    else:
                        query += ' AND tag = ?'
                        params.append(tags)
                
                # Complete the subquery and join
                query += '''
                        GROUP BY tag
                    ) e2 ON e1.tag = e2.tag AND e1.timestamp = e2.max_timestamp
                    WHERE e1.name = ?
                '''
                params.append(name)
                
                # Add tag filter to main query if provided
                if tags is not None:
                    if isinstance(tags, list):
                        if len(tags) == 1:
                            query += ' AND e1.tag = ?'
                            params.append(tags[0])
                        elif len(tags) > 1:
                            placeholders = ','.join(['?'] * len(tags))
                            query += f' AND e1.tag IN ({placeholders})'
                            params.extend(tags)
                    else:
                        query += ' AND e1.tag = ?'
                        params.append(tags)
                
                # Order by tag for consistent results
                query += ' ORDER BY e1.tag'

                # Execute and return results
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except sqlite3.Error as e:
            log.error(f"Error getting latest events by tag: {e}")
            return []


    def get_event_names(self) -> List[str]:
        """
        Get all distinct event names from the database.

        Returns:
            List[str]: List of unique event names
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query to get distinct event names
                query = 'SELECT DISTINCT name FROM Events ORDER BY name'
                
                # Execute and return results
                cursor.execute(query)
                rows = cursor.fetchall()
                return [row[0] for row in rows]

        except sqlite3.Error as e:
            log.error(f"Error getting event names: {e}")
            return []


    def get_event_names_with_counts(self) -> List[Dict[str, Any]]:
        """
        Get all distinct event names from the database along with their record counts.

        Returns:
            List[Dict[str, Any]]: List of dictionaries with 'name' and 'count' keys, sorted by name
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query to get distinct event names with counts
                query = 'SELECT name, COUNT(*) as count FROM Events GROUP BY name ORDER BY name'
                
                # Execute and return results
                cursor.execute(query)
                rows = cursor.fetchall()
                return [{'name': row[0], 'count': row[1]} for row in rows]

        except sqlite3.Error as e:
            log.error(f"Error getting event names with counts: {e}")
            return []


    def delete_old_events(self, name: str, tag: Optional[str], days: int) -> int:
        """
        Delete all events older than the specified number of days.

        Args:
            name (str): Event name to delete.
            tag (str): If provided, will also filter by tag.
            days (int): Number of days. Events older than this will be deleted.

        Returns:
            int: Number of events deleted.
        """
        try:
            with self.get_connection() as conn:

                cursor = conn.cursor()
                
                # Calculate the cutoff date
                cutoff_date = datetime.now() - timedelta(days=days)
                
                if tag:
                    cursor.execute('''
                        DELETE FROM Events
                        WHERE name = ? AND tag = ? AND timestamp < ?
                    ''', (name, tag, cutoff_date))
                else:
                    cursor.execute('''
                        DELETE FROM Events
                        WHERE name = ? AND timestamp < ?
                    ''', (name, cutoff_date))

                deleted_count = cursor.rowcount
                conn.commit()

                print(f"Deleted {deleted_count} events older than {days} days")
                return deleted_count
            
        except sqlite3.Error as e:
            log.error(f"Error deleting old events: {e}")
            return 0


    def close(self) -> None:
        """
        Close the database connection (if using persistent connections).
        Note: This implementation uses context managers, so connections are auto-closed.
        
        Returns:
            None
        """
        pass

