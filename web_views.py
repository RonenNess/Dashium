"""
Build the web views for the application.
Author: Ronen Ness.
Created: 2025.
"""
import os
import web_server
import config
import collect_events_job
from db import DatabaseManager
from web_apis import api_stats

# set by the engine
db: DatabaseManager = None # type: ignore


def to_html(text: str):
    return text.replace('\n', '<br />')


icons = dict(line_chart_up="&#x1F4C8;", line_chart_down="&#x1F4C9;", table="&#x25A4;", bars="&#x1F4CA;", metric="&#x1F5E0;", ballot="&#x1F5F3;", grid="&#x25A6;", calc="&#x1F9EE;", numbers="&#x1F522;", report="&#x1F5C4;", check="&#x2705;", error="&#x274C;", warning="&#x26A0;", priority="&#x26A1;", green_circle="&#x1F7E2;", yellow_circle="&#x1F7E1;", red_circle="&#x1F534;", clipboard="&#x1F4CB;", mobile="&#x1F4F1;", pc="&#x1F4BB;", folder="&#x1F5C2;", database="&#x1F4BE;", signal="&#128246;", wifi="&#128246;", server="&#128187;", stopwatch="&#9201;", star="&#11088;", target="&#127919;", trophy="&#127942;", magnifying_glass="&#128269;", bell="&#128276;", gear="&#9881;", tools="&#128736;", pie="&#9684;", dollar="&#128178;", square_plus="&#8862;", battery="&#128267;", electric_plug="&#128268;", lightning="&#9889;", link="&#128279;", globe="&#127760;", level_slider="&#127898;", termometer="&#127777;", newspaper="Newspaper", bookmark="&#128209;", calendar="&#128197;", lock="&#128274;", unlock="&#128275;", eye="&#128065;", shield="&#128737;", person="&#128100;", office_worker="&#128104;&#8205;&#128188;", money="&#128181;", earth_america="&#127758;", earth_europe="&#127757;", earth_africa="&#127756;", pushpin="&#128205;", red_flag="&#128681;", fire="&#128293;", disk="&#128191;", bug="&#128027;", detective="&#128373;", floppy="&#128190;", scroll="&#x1F9FE;", scroll_old="&#x1F4DC;", doc="&#x1F4C4;", writing="&#x1F4DD;")
def to_html_icon(icon: str):
    if not icon:
        return ""
    return icons.get(icon, icon)


def setup_admin_page(web_server: web_server.WebServer):
    """Setup the admin panel page."""
    context = dict(page_title="Admin Panel", collectors=config.DATA_COLLECTORS, enable_raw_events_page=config.ENABLE_RAW_EVENTS_PAGE)
    def update_admin_data(context: dict, path: str, query_params: dict):

        # add logs data
        if config.LOGS and config.LOGS.get('log_file'):
            
            # load last and current log
            logs_data = ""
            log_path = str(config.LOGS['log_file'])
            if os.path.exists(log_path + ".1"):
                logs_data += "\n----- Previous Log -----\n\n"
                logs_data += open(log_path + ".1", 'r').read()
            if os.path.exists(log_path):
                logs_data += "\n----- Current Log -----\n\n"
                logs_data += open(log_path, 'r').read()

            # set log or no logs available
            if logs_data:
                context["server_logs"] = logs_data
            else:
                context["server_logs"] = "No logs available."

        # add data collectors status
        for collector in context["collectors"]:
            collector['status'] = collect_events_job.get_data_collector_status(collector["module"], collector.get("unique_id", ""))

        # add event names and counters
        context["events"] = db.get_event_names_with_counts()

        # add auth manager info
        if config.AUTHENTICATION_ENABLED:
            from auth import get_auth_manager
            auth_manager = get_auth_manager()
            context["auth_required"] = True
            context["auth_manager"] = {
                "is_locked": auth_manager.is_locked(),
                "lock_until": auth_manager.lock_until,
                "failed_login_attempts": auth_manager.failed_attempts,
                "max_failed_attempts": auth_manager.lock_after_failed_attempts,
            }
        else:
            context["auth_required"] = False
            context["auth_manager"] = {}

        # add API stats
        api_stats_list = []
        for api_name, api_stats_entry in api_stats.items():
            api_stats_list.append({
                "api_name": api_name,
                "total_calls": api_stats_entry.total_requests,
                "total_errors": api_stats_entry.total_errors,
                "avg_response_time_ms": round(api_stats_entry.average_response_time_ms, 2),
                "max_response_time_ms": round(api_stats_entry.max_response_time_ms, 2),
            })
        context["api_stats"] = api_stats_list
        
        # add sessions data
        if config.AUTHENTICATION_ENABLED:
            from auth import get_auth_manager
            auth_manager = get_auth_manager()
            context["active_sessions"] = auth_manager.get_active_sessions_info()
        else:
            context["active_sessions"] = []

    # register the admin view
    web_server.register_view(['/admin'], "admin.html", context, update_admin_data)


def setup_raw_events_fetch_page(web_server: web_server.WebServer):
    """Setup the events fetch page."""
    context = dict(page_title="Events Data", collectors=config.DATA_COLLECTORS)
    def update_events_fetch_data(context: dict, path: str, query_params: dict):
        event_name = query_params.get("name")
        context["event_name"] = event_name
        if event_name:
            context["events"] = db.get_events(event_name, max_results=10000)
        else:
            context["events"] = []

    # register the events fetch view
    web_server.register_view(['/events'], "events.html", context, update_events_fetch_data)


def register_web_views(web_server: web_server.WebServer):
    """Register all web views to a given web server."""

    # home page
    dashboards = [dict(title=d.get('title', d.get('id')), icon=to_html_icon(d.get('icon', '')), description=d.get('inline_description', ''), url='dashboard/' + d.get('url', d.get('id'))) for d in config.VIEWS]
    context = dict(page_title="Home", home_page_intro=config.WEB_VIEWS.get("home_page_intro", ""), dashboard_name="Home", dashboards=dashboards)
    web_server.register_view(['/', ''], "index.html", context)

    # admin panel page
    if config.ENABLE_ADMIN_PANEL:
        setup_admin_page(web_server)

    # raw events fetch page
    if config.ENABLE_RAW_EVENTS_PAGE:
        setup_raw_events_fetch_page(web_server)

    # add login / logout
    if config.AUTHENTICATION_ENABLED:
        def process_login_context(context: dict, path: str, query_params: dict):
            """Process login page context to include next parameter"""
            context['next_url'] = query_params.get('next', '/')
        
        context = dict(page_title="Login")
        web_server.register_view([f'/login'], "login.html", context, process_context=process_login_context)
        context = dict(page_title="Logout")
        web_server.register_view([f'/logged_out_page'], "logout.html", context)

    # register all dashboards from config views
    for view in config.VIEWS:
        
        # get id and make sure exists
        id = view.get('id')
        if not id:
            raise ValueError("Missing 'id' for view!")
        
        # get url and title
        url = view.get('url', id)
        title = view.get('title', id)

        # create context and register view
        context = dict(
            page_title = title, 
            dashboard_name = title, 
            default_event_name_param = view.get('default_event_name_param', ''),
            event_name_param_choices = view.get('event_name_param_choices', []),
            event_name_param_label = view.get('event_name_param_label', ''),
            show_page_time_aggregation_selection = view.get('show_page_time_aggregation_selection', True),
            data_sources = view.get('data', []),
            widgets = view.get('widgets', []),
            default_time_aggregation = view.get('default_time_aggregation', 'disabled'),
            description = to_html(view.get('long_description') or view.get('inline_description') or ""),
        )
        web_server.register_view([f'/dashboard/{url}'], "dashboard.html", context)

