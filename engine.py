"""
Main engine module.
Handles initialization, data collection scheduling, and web server startup.
This is the main entry point for the application.
Author: Ronen Ness.
Created: 2025.
"""
import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import List

print(r"""
  _____            _     _                 
 |  __ \          | |   (_)                
 | |  | | __ _ ___| |__  _ _   _ _ __ ___  
 | |  | |/ _` / __| '_ \| | | | | '_ ` _ \ 
 | |__| | (_| \__ \ | | | | |_| | | | | | |
 |_____/ \__,_|___/_| |_|_|\__,_|_| |_| |_| v1.0.4
                                           
   ^ by Ronen Ness, 2025       
""")

# get application directory 
root_dir : str = os.path.dirname(os.path.abspath(__file__))

# get application name to run
if len(sys.argv) <= 1:
    sys.stderr.write("No application specified to run. Usage: python engine.py <app_name>\n")
    exit(1)

# add application to path
app_name : str = sys.argv[1]
app_dir : str = os.path.join(root_dir, app_name)
import sys
sys.path.append(app_dir)

# load application config and inject it into the config module, which serves as a template
# that way we have a single config module to import from other modules + we have auto complete in IDEs
import config
app_config_path = Path(os.path.join(app_dir, 'config.py'))
spec = importlib.util.spec_from_file_location(app_config_path.stem, app_config_path) # type: ignore
app_config_module = importlib.util.module_from_spec(spec) # type: ignore
sys.modules[app_config_path.stem] = app_config_module # type: ignore
spec.loader.exec_module(app_config_module) # type: ignore
config.__dict__.clear()
config.__dict__.update(app_config_module.__dict__)

# sanity
if config.IS_EXAMPLE_CONFIG:
    sys.stderr.write("Error: You are trying to run the template application configuration file. Something went wrong with configuration injection, or your application contains engine.py file, which it should not.\n")
    exit(1)

# if missing, create data folder
if not os.path.exists(config.DATA_DIR):
    os.makedirs(config.DATA_DIR)

# if missing, create logs folder
if not os.path.exists(config.LOGS_DIR):
    os.makedirs(config.LOGS_DIR)

# load other modules - must happen after updating path
import logger
from data_collector import DataCollector
from db import DatabaseManager
import web_server

# get logger
log = logger.get_logger("engine")
log.info("Engine started.")
log.info(f"Load application {app_name} from path '{app_dir}'.")

# load data collectors
data_collectors: List[DataCollector] = []
for ds_config in config.DATA_COLLECTORS:

    # get collector module name
    module = ds_config.get("module")
    if not module:
        log.warning("Data collector configuration missing 'module' key.")
        exit(1)

    # get collection interval and config
    interval = ds_config.get("collect_interval_in_minutes", 10)
    module_config = ds_config.get("config", {})
    
    # create data collector instance
    data_collector = DataCollector(module, interval, module_config, unique_id=ds_config.get("unique_id", ""))
    data_collectors.append(data_collector)
    log.info(f"Loaded data collector module: {module}")


# init db
log.info("Initializing database.")
db = DatabaseManager(str(config.DATABASE['db_path']))
db.connect()
db.init_database()


# add the collect events job
log.info("Init job to run event collectors..")
import collect_events_job
collect_events_job.data_collectors = data_collectors
collect_events_job.db = db

# add the delete old events job
log.info("Init job to delete old events..")
import delete_old_events_job
delete_old_events_job.data_collectors = data_collectors
delete_old_events_job.db = db

# Create the web application!
log.info("Initialize web server..")
web_server_config = config.WEB_SERVER_CONFIG
host = web_server_config.get("host", "localhost")
enable_https = web_server_config.get("enable_https", False)

# Choose appropriate port based on HTTPS setting
if enable_https:
    port = web_server_config.get("https_port", 8443)
else:
    port = web_server_config.get("port", 8080)

static_files_dir = web_server_config.get("static_files_dir", str(config.ENGINE_DIR / "web_assets"))

# Ensure proper types
if not isinstance(host, str):
    raise TypeError("Invalid type for host")
if not isinstance(port, int):
    raise TypeError("Invalid type for port")
if not isinstance(static_files_dir, str):
    raise TypeError("Invalid type for static_files_dir")

# Extract SSL configuration
ssl_config = {
    "enable_https": enable_https,
    "ssl_cert_file": web_server_config.get("ssl_cert_file"),
    "ssl_key_file": web_server_config.get("ssl_key_file"),
    "ssl_cert_chain_file": web_server_config.get("ssl_cert_chain_file"),
    "ssl_check_hostname": web_server_config.get("ssl_check_hostname", True),
    "ssl_verify_mode": web_server_config.get("ssl_verify_mode", "CERT_REQUIRED")
}

web_server_instance = web_server.WebServer(
    host=host,
    port=port,
    require_auth=config.AUTHENTICATION_ENABLED,
    web_assets_dir=Path(static_files_dir),
    config_dict=config.WEB_VIEWS,
    ssl_config=ssl_config,
    app_path=app_dir
)

# init auth manager
import auth
auth_manager = auth.init_auth_manager(session_timeout_hours=config.SESSION_TIMEOUT_HOURS, 
                                      lock_after_failed_attempts=config.LOCK_AUTHENTICATION_AFTER_FAILED_ATTEMPTS.get("max_attempts", 0), 
                                      lock_after_failed_attempts_time_minutes=config.LOCK_AUTHENTICATION_AFTER_FAILED_ATTEMPTS.get("lockout_duration_minutes", 30))
# init users
log.info("Initialize users..")
for user in config.USERS:
    username = user.get("username")
    password = user.get("password")
    if username and password:
        auth_manager.create_user(username, password)
        log.info(f"Added user: {username}")
    else:
        log.warning("User configuration missing 'username' or 'password' key.")

# init web views
log.info("Initialize web server views..")
import web_views
web_views.db = db
web_views.register_web_views(web_server=web_server_instance)

# init web apis
log.info("Initialize web server APIs..")
import web_apis
web_apis.register_web_apis(db=db, web_server=web_server_instance)

# start the web server
log.info("Starting web server.")
try:
    web_server_instance.start()
except:
    log.error("Engine did not start because of error in web server.")
    exit(1)