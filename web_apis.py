"""
Build the web APIs for the application.
Author: Ronen Ness.
Created: 2025.
"""
from cmath import log
from typing import Dict, Any, List, Tuple, Optional
import web_server
import db
import config
from datetime import datetime
import logger

log = logger.get_logger(__name__)

class APIStats:
    """Class to hold API statistics."""
    def __init__(self):
        self.total_requests: int = 0
        self.total_errors: int = 0
        self.average_response_time_ms: float = 0.0
        self.max_response_time_ms: float = 0.0

    def update_times(self, response_time_ms: float) -> None:
        """Update average and max response times."""
        self.average_response_time_ms = (
            (self.average_response_time_ms * (self.total_requests - 1) + response_time_ms)
            / self.total_requests
        )
        if response_time_ms > self.max_response_time_ms:
            self.max_response_time_ms = response_time_ms

# apis stats
# key is url, value is API stats
api_stats = {}


def register_web_apis(db: db.DatabaseManager, web_server: web_server.WebServer) -> None:
    """
    Register all web apis to a given web server.
    
    Args:
        db (db.DatabaseManager): Database manager instance
        web_server (web_server.WebServer): Web server instance to register APIs with
        
    Returns:
        None
    """
    
    # api to fetch events
    def fetch_events_api(query_params: Dict[str, str]) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch events from the database based on query parameters.
        
        Args:
            query_params (Dict[str, str]): Query parameters from the request
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: List of events and HTTP status code
        """
        # get api stats to update
        global api_stats
        stats_key = ";".join(f"{k}={v}" for k, v in query_params.items())
        if stats_key not in api_stats:
            api_stats[stats_key] = APIStats()
        api_stats_entry = api_stats[stats_key]
        api_stats_entry.total_requests += 1

        # get time measurement before fetching
        start_time = datetime.now()

        # query_params = {'name': 'example_event', 'max_age_days': '10'}
        name = query_params.get("name")
        if not name:
            api_stats_entry.total_errors += 1
            return [], 400  # Bad request if no name provided

        try:

            # special - if last_unique_by_tag is set, get only the latest event for each tag
            if query_params.get("last_unique_by_tag", "false").lower() == "true":
                events = db.get_latest_events_by_tag(
                    name=name,
                    tags=query_params.get("tag")
                )
                api_stats_entry.update_times((datetime.now() - start_time).total_seconds() * 1000)
                return events, 200

            # fetch events based on other parameters
            events = db.get_events(
                name=name,
                tags=query_params.get("tag"),
                max_age_days=int(query_params.get("max_age_days", 0)),
                max_results=int(query_params.get("max_results", 0))
            )

            # log time taken
            api_stats_entry.update_times((datetime.now() - start_time).total_seconds() * 1000)
            
            # return results
            return events, 200
        
        except Exception as e:
            api_stats_entry.total_errors += 1
            log.error(f"Error fetching events for API: {e}")
            raise e

    web_server.register_api(urls=["/api/events"], callback=fetch_events_api)

    # POST API to add events (only if enabled in config)
    if config.PUSH_EVENTS_API_CONFIG.get("enable", False):
        def add_events_api(data: Dict[str, Any], headers: Dict[str, str]) -> Tuple[Dict[str, Any], int]:
            """
            Add events to the database via POST request.
            
            Args:
                data (Dict[str, Any]): Request body data containing events
                headers (Dict[str, str]): Request headers including API key
                
            Returns:
                Tuple[Dict[str, Any], int]: Response data and HTTP status code
            """
            # Validate API key
            api_key = headers.get("X-API-Key") or headers.get("Authorization", "").replace("Bearer ", "")
            expected_key = config.PUSH_EVENTS_API_CONFIG.get("api_key")
            
            if not api_key or api_key != expected_key:
                return {"error": "Invalid or missing API key"}, 401
            
            # Validate request data
            if not isinstance(data, dict):
                return {"error": "Request body must be a JSON object"}, 400
                
            events_data = data.get("events")
            if not events_data:
                return {"error": "Missing 'events' field in request body"}, 400
                
            if not isinstance(events_data, list):
                return {"error": "'events' field must be an array"}, 400
                
            if len(events_data) == 0:
                return {"error": "Events array cannot be empty"}, 400
            
            # Validate and process events
            processed_events = []
            for i, event_data in enumerate(events_data):
                if not isinstance(event_data, dict):
                    return {"error": f"Event at index {i} must be an object"}, 400
                
                # Required fields
                name = event_data.get("name")
                if not name or not isinstance(name, str):
                    return {"error": f"Event at index {i} missing required 'name' field (string)"}, 400
                
                # Optional fields with defaults
                value = event_data.get("value", 0)
                if not isinstance(value, (int, float)):
                    return {"error": f"Event at index {i} 'value' field must be a number"}, 400
                
                tag = event_data.get("tag")
                if tag is not None and not isinstance(tag, str):
                    return {"error": f"Event at index {i} 'tag' field must be a string if provided"}, 400
                
                additional_info = event_data.get("additional_info")
                if additional_info is not None and not isinstance(additional_info, str):
                    return {"error": f"Event at index {i} 'additional_info' field must be a string if provided"}, 400
                
                # Handle timestamp
                timestamp = None
                timestamp_str = event_data.get("timestamp")
                if timestamp_str:
                    try:
                        # Try to parse ISO format timestamp
                        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        return {"error": f"Event at index {i} invalid timestamp format. Use ISO format (e.g., '2025-01-01T12:00:00Z')"}, 400
                
                processed_events.append({
                    "name": name,
                    "value": int(value),
                    "tag": tag,
                    "additional_info": additional_info,
                    "timestamp": timestamp
                })
            
            # Insert events into database
            try:
                success = db.insert_events_bulk(processed_events)
                if success:
                    return {
                        "message": f"Successfully added {len(processed_events)} events",
                        "events_count": len(processed_events)
                    }, 201
                else:
                    return {"error": "Failed to insert events into database"}, 500
            except Exception as e:
                return {"error": f"Database error: {str(e)}"}, 500

        # Register the POST API endpoint
        endpoint_url = config.PUSH_EVENTS_API_CONFIG.get("url", "/api/events")
        web_server.register_post_api(urls=[endpoint_url], callback=add_events_api)