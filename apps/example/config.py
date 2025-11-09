"""
Example application configuration template.
Author: Ronen Ness.
Created: 2025.
"""
from pathlib import Path
from typing import List, Dict
import os

# this should never be True in real config files
IS_EXAMPLE_CONFIG: bool = os.path.exists(os.path.join(Path(__file__).parent, "engine.py")) and os.path.exists(os.path.join(Path(__file__).parent, "data_collector.py"))

# application name and folder path
APP_NAME: str = Path(__file__).stem
APP_DIR: Path = Path(__file__).parent

# the path of the engine itself
ENGINE_DIR: Path = Path(os.path.join(str(APP_DIR), "..", ".."))

# engine path sanity
if not IS_EXAMPLE_CONFIG and not os.path.exists(ENGINE_DIR / "engine.py"):
    raise RuntimeError("Missing engine.py file! All Dashium applications must be located under Dashium /apps/<app_name>/ path or they won't work.")

# data folder path
DATA_DIR: Path = APP_DIR / "data"

# logs folder path
LOGS_DIR: Path = APP_DIR / "logs"

# database configuration
DATABASE: Dict = {
    "db_path": DATA_DIR / "events.db"
}

# logs configuration
LOGS: Dict = {
    "format": "%(levelname)s | %(asctime)s | %(name)s | %(message)s",
    "enable_log_file": True,
    "enable_console_log": True,
    "log_level": "INFO",
    "log_file": LOGS_DIR / "app.log",
    "max_bytes": 1024*1024*10,
    "backup_count": 3
}

# interval in minutes to run the event collectors task
COLLECT_EVENTS_TASK_INTERVAL_MINUTES: int = 1

# interval in minutes to run the events deletion task
DELETE_OLD_EVENTS_TASK_INTERVAL_MINUTES: int = 60

# if true, will enable the admin panel page showing system status, logs, and data collectors info
ENABLE_ADMIN_PANEL: bool = True

# if true, will enable a page to view events raw data
ENABLE_RAW_EVENTS_PAGE: bool = True


# data collectors to register
DATA_COLLECTORS: List[Dict] = []

# allow additional data collectors config in seperate file
try:
    import config_data_collectors  # type: ignore
    for collector in config_data_collectors.DATA_COLLECTORS:
        DATA_COLLECTORS.append(collector)
except ModuleNotFoundError:
    pass


# views (dashboards) to register
VIEWS: List[Dict] = []

# allow additional views config in seperate file
try:
    import config_views  # type: ignore
    for view in config_views.VIEWS:
        VIEWS.append(view)
except ModuleNotFoundError:
    pass


# web server configuration - host and port to serve on
WEB_SERVER_CONFIG: Dict = {
    "host": "localhost",
    "port": 8080,
    "static_files_dir": os.path.join(ENGINE_DIR, "web_assets"),
    
    # HTTPS/SSL Configuration
    "enable_https": False,                    # Enable HTTPS instead of HTTP
    "ssl_cert_file": None,                    # Path to SSL certificate file (.pem or .crt)
    "ssl_key_file": None,                     # Path to SSL private key file (.key)
    "ssl_cert_chain_file": None,              # Optional: Path to certificate chain file
    "https_port": 8443,                       # Port to use for HTTPS (when enable_https is True)
    
    # SSL/TLS Options
    "ssl_check_hostname": True,               # Whether to check SSL hostname
    "ssl_verify_mode": "CERT_REQUIRED"        # SSL verification mode: "CERT_NONE", "CERT_OPTIONAL", "CERT_REQUIRED"
    
    # Example HTTPS configuration:
    # "enable_https": True,
    # "ssl_cert_file": "/path/to/certificate.pem",
    # "ssl_key_file": "/path/to/private.key",
    # "https_port": 8443,
    # "ssl_check_hostname": False,            # Set to False for self-signed certificates
    # "ssl_verify_mode": "CERT_NONE"          # Set to CERT_NONE for self-signed certificates
}

# configure the web application texts, views, and pages
# use it to customize what you see in the web application
WEB_VIEWS: Dict = {
    "application_name": "Dashium Demo",
    "home_page_intro": "This example application demonstrates some of Dashium's capabilities.",
    "top_bar_links": [
        {"title": "Dashboards", "url": "/"}
    ],
    "enable_admin_panel": ENABLE_ADMIN_PANEL
}
if ENABLE_ADMIN_PANEL:
    WEB_VIEWS["top_bar_links"].append({"title": "Admin", "url": "/admin"})

# enable user authentication
AUTHENTICATION_ENABLED: bool = True

# user authentication details
USERS: List[dict] = [
    {
        "username": "admin",
        "password": "admin"
    }
]

# session timeout in hours
SESSION_TIMEOUT_HOURS: int = 4

# lock authentication after failed multiple attempts configuration
LOCK_AUTHENTICATION_AFTER_FAILED_ATTEMPTS: Dict = {
    "max_attempts": 15,
    "lockout_duration_minutes": 30
}

# API configuration for POST events endpoint
PUSH_EVENTS_API_CONFIG: Dict = {
    "enable": True,
    "api_key": "your-secret-api-key-here",  # Change this to a secure random string
    "url": "/api/events"
}