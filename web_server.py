"""
Built-in web server to serve the web application and static files.
Author: Ronen Ness.
Created: 2025.
"""
import http.server
import socketserver
import ssl
import datetime
import urllib.parse
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Callable
import logger
from template_engine import ITemplateEngine, create_template_engine
import copy
from types import FunctionType
import auth


log = logger.get_logger(__name__)

class View:
    """Represent a view: template + context, and URLs that should load it."""
    urls: List[str] = []
    template: str = ""
    context: Dict[str, Any] = dict()
    process_context: Optional[FunctionType] = None
    def __init__(self, urls: List[str], template: str, context: Dict[str, Any], process_context: Optional[FunctionType] = None) -> None:
        """
        Initialize a View.
        
        Args:
            urls (List[str]): List of URL patterns
            template (str): Template name to render
            context (Dict[str, Any]): Context data for template
            process_context (Optional[FunctionType]): Optional function to process context
            
        Returns:
            None
        """
        self.urls = urls
        self.template = template
        self.context = context
        self.process_context = process_context
        
class API:
    """Represent an API: callback, and URLs that should load it."""
    urls: List[str] = []
    callback: Callable[..., Any] = None # type: ignore
    def __init__(self, urls: List[str], callback: Callable[..., Any]) -> None:
        """
        Initialize an API endpoint.
        
        Args:
            urls (List[str]): List of URL patterns
            callback (Callable[..., Any]): Callback function for the API endpoint
            
        Returns:
            None
        """
        self.urls = urls
        self.callback = callback

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler for serving static files and handling API requests"""

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialize the custom HTTP request handler.
        
        Args:
            *args: Positional arguments for parent class
            **kwargs: Keyword arguments for parent class
            
        Returns:
            None
        """
        # Get configuration from class attributes (set by factory function)
        self.config : Dict = getattr(self.__class__, 'config', None) # type: ignore
        self.web_assets_dir : Path = getattr(self.__class__, 'web_assets_dir', None) # type: ignore
        self.template_engine : ITemplateEngine = getattr(self.__class__, 'template_engine', None) # type: ignore
        self.views : List[View] = getattr(self.__class__, 'views', None) # type: ignore
        self.get_apis : List[API] = getattr(self.__class__, 'get_apis', None) # type: ignore
        self.post_apis : List[API] = getattr(self.__class__, 'post_apis', None) # type: ignore
        self.auth_required : bool = getattr(self.__class__, 'auth_required', False) # type: ignore
        super().__init__(*args, directory=str(self.web_assets_dir), **kwargs)
    

    def do_GET(self) -> None:
        """
        Handle GET requests
        
        Returns:
            None
        """
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query_params = dict(urllib.parse.parse_qsl(parsed_path.query))
        
        # get cookies
        cookies = self.get_cookies()

        # user by default is None unless logged in
        user = None

        # handle login / logouts
        if self.auth_required:

            # get auth manager
            auth_manager: auth.AuthenticationManager = auth.get_auth_manager()

            # special - logout
            if path == "/logout":
                auth_token: Optional[str] = cookies.get("auth_token", None)
                if auth_token:
                    auth_manager.logout(auth_token)
                    log.info(f"User logged out: {auth_token}")

                # Redirect to logged out page after logout
                self.send_response(302)
                self.send_header('Location', '/logged_out_page')
                self.send_header('Set-Cookie', 'auth_token=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly')
                self.end_headers()
                return

            # if auth is enabled, check for auth cookie
            elif not path.startswith('/static/') and not path == "/login" and not path == "/logged_out_page":

                # try to get logged in user
                auth_token: Optional[str] = cookies.get("auth_token", None)
                if auth_token:
                    try:
                        user = auth_manager.retrieve_user_by_session_id(auth_token)
                    except Exception as e:
                        log.warning(f"Error retrieving user by session ID: {e}")
                        user = None
                
                # no user found? if its api, return 401, else redirect to login
                if not user:
                    if path.startswith('/api/'):
                        log.warning(f"Unauthorized access attempt to {path} - invalid or missing auth token.")
                        self.send_response(401)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(b'Unauthorized: Please log in to access this resource.')
                    else:
                        redirect_url = f'/login?next={urllib.parse.quote(self.path)}'
                        self.send_response(302)
                        self.send_header('Location', redirect_url)
                        self.end_headers()
                    return

        # handle API requests
        if path.startswith('/api/'):
            self.handle_api_request(path, query_params, cookies, user)

        # serve static files
        elif path.startswith('/static/'):
            self.serve_static_file(path, cookies, user)
                    
        # handle specific pages
        elif path.startswith('/') or path == '':
            self.handle_pages(path, query_params, cookies, user)
        
        else:
            log.error(f"Unhandled GET request path: {path}")
            self.send_error(404, "File not found")
    
    def do_POST(self) -> None:
        """
        Handle POST requests
        
        Returns:
            None
        """
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # Handle login POST request
        if path == "/api/login":
            self.handle_login_post()

        # Handle registered API POST requests
        elif path.startswith('/api/'):
            self.handle_api_post_request(path)

        # Unknown POST request
        else:
            log.error(f"Unhandled POST request path: {path}")
            self.send_error(404, "Endpoint not found")
    

    def handle_login_post(self) -> None:
        """
        Handle POST request to /api/login endpoint
        
        Returns:
            None
        """
        try:
            
            # get auth manager
            auth_manager: auth.AuthenticationManager = auth.get_auth_manager()
            
            # Get the content length
            content_length = int(self.headers.get('Content-Length', 0))
            
            # Read the POST data
            post_data = self.rfile.read(content_length)
            
            # Parse the JSON data
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                log.warning("Invalid JSON in login request")
                self.send_json_response({"error": "Invalid JSON format"}, 400)
                return
            
            # Extract username, password, and next URL
            username = data.get('username', '').strip()
            password = data.get('password', '')
            next_url = data.get('next', '/').strip()
            
            # Validate next URL to prevent open redirects
            if next_url and not next_url.startswith('/'):
                next_url = '/'
            
            # Validate input
            if not username or not password:
                log.warning("Login attempt with missing username or password")
                self.send_json_response({"error": "Username and password are required"}, 400)
                return
            
            # Check if auth manager is locked
            try:
                if auth_manager.is_locked():
                    log.warning(f"Login attempt for '{username}' rejected - auth manager is locked")
                    self.send_json_response({
                        "error": "Authentication is temporarily disabled due to too many failed attempts. Please try again later."
                    }, 423)  # 423 Locked
                    return
                
                # Attempt authentication
                auth_result = auth_manager.authenticate(username, password)
            except Exception as auth_error:
                log.error(f"Error during authentication for '{username}': {auth_error}")
                self.send_json_response({"error": "Authentication service temporarily unavailable"}, 503)
                return
            
            if auth_result is not None:
                # Success: authentication succeeded
                user, session_id = auth_result
                log.info(f"Successful login for user '{username}'")
                
                # Set auth cookie and redirect to next URL or root
                response_data = {
                    "success": True,
                    "message": "Login successful",
                    "redirect": next_url if next_url else "/"
                }
                
                # Send response with cookie
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Set-Cookie', f'auth_token={session_id}; Path=/; HttpOnly')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                return
            
            else:
                # Failure: wrong credentials or manager locked
                if auth_manager.is_locked():
                    # Manager became locked during authentication attempt
                    log.warning(f"Auth manager locked after failed login attempt for '{username}'")
                    self.send_json_response({
                        "error": "Authentication is temporarily disabled due to too many failed attempts. Please try again later."
                    }, 423)  # 423 Locked
                else:
                    # Wrong username/password
                    log.warning(f"Failed login attempt for '{username}' - invalid credentials")
                    self.send_json_response({
                        "error": "Invalid username or password"
                    }, 401)  # 401 Unauthorized
                    
        except Exception as e:
            log.error(f"Error processing login request: {e}")
            self.send_json_response({"error": "Internal server error"}, 500)
            return
    

    def send_json_response(self, data: Dict[str, Any], status_code: int = 200) -> None:
        """
        Send a JSON response with the specified data and status code
        
        Args:
            data (Dict[str, Any]): Data to send as JSON
            status_code (int): HTTP status code
            
        Returns:
            None
        """
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
        

    def handle_pages(self, path: str, query_params: Dict[str, str], cookies: Dict[str, str], user: Optional[auth.User]):
        """
        Handle specific page requests
        Args:
            path (str): The request path
            query_params (Dict[str, str]): Query parameters from the URL
            cookies (Dict[str, str]): Cookies from the request
            user (Optional[auth.User]): Authenticated user, if any
        """
        for view in self.views:
            if path in view.urls:

                # get context
                context = view.context
                context = copy.deepcopy(context) if context else {}
                
                # set default context values
                config_dict: dict = self.config
                context.update({
                    'current_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'server_info': config_dict.get("server_info", "Dashium Analytics Web Server 1.0 | Made by Ronen Ness, 2025"),
                    'site_title': config_dict.get("application_name", "Unnamed Application"),
                    'top_bar_links': config_dict.get("top_bar_links", []),
                    "enable_admin_panel": config_dict.get("enable_admin_panel", False),
                    "show_logout_button": self.auth_required and user,
                    "show_login_button": self.auth_required and not user,
                    "user": user
                })

                # if need to process it, clone and process the clone
                if view.process_context:
                    view.process_context(context, path, query_params)

                # if no user but auth cookie appears, delete it
                extra_headers_func: Optional[FunctionType] = None
                if user is None and 'auth_token' in cookies:
                    def delete_cookie_func(handler: http.server.BaseHTTPRequestHandler):
                        handler.delete_cookie("auth_token") # type: ignore
                    extra_headers_func = delete_cookie_func

                # render the template with updated context
                self.render_template(view.template, context, extra_headers=extra_headers_func)
                return
            
        self.send_error(404, f"View not found for {path}")


    def handle_api_request(self, path: str, query_params: Dict[str, str], cookies: Dict[str, str], user: Optional[auth.User]) -> None:
        """
        Placeholder function for handling API GET requests
        
        Args:
            path (str): The request path (e.g., '/api/data')
            query_params (Dict[str, str]): Query parameters from the URL
            cookies (Dict[str, str]): Cookies from the request
            user (Optional[auth.User]): Authenticated user, if any

        Returns:
            None
        """
        for api in self.get_apis:
            if path in api.urls:

                try:
                    data, status = api.callback(query_params)
                    response_data = {
                        "data": data
                    }
                    self.send_response(status or 200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')  # Enable CORS
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                    return
                
                except Exception as e:
                    log.error(f"Error occurred while processing API request: {e}")
                    self.send_error(500, "Internal Server Error")
                    return
                
        self.send_error(404, f"API endpoint not found for {path}")


    def handle_api_post_request(self, path: str) -> None:
        """
        Handle API POST requests
        
        Args:
            path (str): The request path (e.g., '/api/events')

        Returns:
            None
        """
        # Check if we have a registered POST API for this path
        for api in getattr(self, 'post_apis', []):
            if path in api.urls:
                try:
                    # Get the content length
                    content_length = int(self.headers.get('Content-Length', 0))
                    
                    # Read the POST data
                    post_data = self.rfile.read(content_length)
                    
                    # Parse the JSON data
                    try:
                        data = json.loads(post_data.decode('utf-8'))
                    except json.JSONDecodeError:
                        log.warning(f"Invalid JSON in POST request to {path}")
                        self.send_json_response({"error": "Invalid JSON format"}, 400)
                        return
                    
                    # Get headers for authentication
                    headers = dict(self.headers)
                    
                    # Call the API callback with data and headers
                    response_data, status = api.callback(data, headers)
                    
                    self.send_response(status or 200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')  # Enable CORS
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                    return
                
                except Exception as e:
                    log.error(f"Error occurred while processing API POST request: {e}")
                    self.send_error(500, "Internal Server Error")
                    return
                
        self.send_error(404, f"API POST endpoint not found for {path}")
                        

    def serve_static_file(self, path: str, cookies: Dict[str, str], user: Optional[auth.User]) -> None:
        """
        Serve static files from web_assets folder or render templates
        
        Args:
            path (str): The file path to serve
            cookies (Dict[str, str]): Cookies from the request
            user (Optional[auth.User]): Authenticated user, if any

        Returns:
            None
        """
        # If path is root, serve index.html
        if path == '/' or path == '':
            path = '/index.html'
        
        # Remove leading slash for file system path
        file_path = self.web_assets_dir / path.lstrip('/')
        
        try:
            if file_path.exists() and file_path.is_file():
                super().do_GET()

            else:
                # File not found, serve 404
                self.send_error(404, f"File not found: {path}")
                log.warning(f"File not found: {file_path}")

        except Exception as e:
            self.send_error(500, f"Internal server error: {str(e)}")
            log.error(f"Error serving file {file_path}: {e}")
    
    
    def get_cookies(self) -> Dict[str, str]:
        """
        Extract cookies from the request headers.
        
        Returns:
            Dict[str, str]: Dictionary of cookie name-value pairs
        """
        cookies = {}
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
            # Parse cookies manually
            for cookie in cookie_header.split(';'):
                if '=' in cookie:
                    name, value = cookie.strip().split('=', 1)
                    cookies[name] = value
        return cookies

    def delete_cookie(self, name: str, path: str = "/") -> None:
        """
        Delete a cookie by setting it to expire in the past.
        
        Args:
            name (str): Cookie name to delete
            path (str): Cookie path (default: "/")
            
        Returns:
            None
        """
        # Set cookie with past expiration date to delete it
        cookie_str = f"{name}=; Path={path}; Expires=Thu, 01 Jan 1970 00:00:00 GMT"
        self.send_header('Set-Cookie', cookie_str)

    def render_template(self, template_name: str, context: Optional[Dict[str, Any]] = None, extra_headers: Optional[FunctionType] = None) -> None:
        """
        Render a template with context data
        
        Args:
            template_name (str): Name of the template to render
            context (Optional[Dict[str, Any]]): Context data for the template
            
        Returns:
            None
        """

        # create default context
        if context is None:
            context = {}
        
        try:
            # Render the template
            template_engine = self.template_engine
            if template_engine is None:
                raise Exception("Template engine not initialized")
            rendered_content = template_engine.render_template(template_name, context)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            if extra_headers:
                extra_headers(self)
            self.end_headers()
            self.wfile.write(rendered_content.encode('utf-8'))
            log.debug(f"Rendered template: {template_name}")
            
        except Exception as e:
            log.error(f"Error rendering template {template_name}: {e}")
            self.send_error(500, f"Template rendering error: {str(e)}")


def create_handler_with_config(config_dict: Dict[str, Any], web_assets_dir: Union[str, Path], template_engine: Optional[ITemplateEngine], views_list: List[Any], get_apis_list: List[Any], post_apis_list: List[Any], is_auth_required: bool) -> type:
    """
    Factory function to create a CustomHTTPRequestHandler with custom configuration.
    
    Args:
        config_dict (Optional[Dict[str, Any]]): Custom configuration dictionary
        web_assets_dir (Union[str, Path]): Custom web assets directory path
        template_engine (Optional[ITemplateEngine]): Custom template engine instance
        views_list (List[Any]): views list. Can start empty and fill in later
        get_apis_list (List[Any]): GET apis list. Can start empty and fill in later
        post_apis_list (List[Any]): POST apis list. Can start empty and fill in later
        is_auth_required (bool): Whether to require authentication

    Returns:
        type: A configured CustomHTTPRequestHandler class
    """
    # determine assets dir
    if web_assets_dir is None:
        assets_dir = Path(__file__).parent / "web_assets"
    elif isinstance(web_assets_dir, str):
        assets_dir = Path(web_assets_dir)
    else:
        assets_dir = web_assets_dir
    
    # default template engine
    template_eng = template_engine or create_template_engine(assets_dir / "templates")

    class ConfiguredHandler(CustomHTTPRequestHandler):
        config: Dict[str, Any] = config_dict
        web_assets_dir: Path = assets_dir
        template_engine: ITemplateEngine = template_eng
        views: List[Any] = views_list
        get_apis: List[Any] = get_apis_list
        post_apis: List[Any] = post_apis_list
        auth_required: bool = is_auth_required

    return ConfiguredHandler


class WebServer:
    """Serve the web application and static files."""
    
    def __init__(self, host: str = 'localhost', port: int = 8000, require_auth: bool = False, config_dict: Optional[Dict[str, Any]] = None, web_assets_dir: Optional[Path] = None, template_engine: Optional[ITemplateEngine] = None, ssl_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the WebServer.
        
        Args:
            host (str): Host address to bind to
            port (int): Port number to bind to
            require_auth (bool): Whether to require authentication
            config_dict (Optional[Dict[str, Any]]): Configuration dictionary
            web_assets_dir (Optional[Path]): Path to web assets directory
            template_engine (Optional[ITemplateEngine]): Custom template engine instance
            ssl_config (Optional[Dict[str, Any]]): SSL configuration dictionary
            
        Returns:
            None
        """
        self.host = host
        self.port = port
        self.server = None
        self.config_dict = config_dict or dict()
        self.web_assets_dir = web_assets_dir or Path(__file__).parent / "web_assets"
        self.template_engine = template_engine or create_template_engine(self.web_assets_dir / "templates")
        self.views = []
        self.get_apis = []
        self.post_apis = []
        self.auth_required = require_auth
        self.ssl_config = ssl_config or dict()

    def start(self) -> None:
        """
        Start the web server.
        
        Returns:
            None
        """
        try:
            # Create handler with configuration
            handler_class = create_handler_with_config(
                config_dict=self.config_dict,
                web_assets_dir=str(self.web_assets_dir),
                template_engine=self.template_engine,
                views_list=self.views,
                get_apis_list=self.get_apis,
                post_apis_list=self.post_apis,
                is_auth_required = self.auth_required
            )
            
            # Create the server with threading support
            self.server = socketserver.ThreadingTCPServer((self.host, self.port), handler_class)
            
            # Configure HTTPS if enabled
            if self.ssl_config.get('enable_https', False):
                self._configure_https()
                protocol = "https"
            else:
                protocol = "http"
            
            log.info(f"Starting web server at {protocol}://{self.host}:{self.port}")
            log.info(f"Serving static files from: {self.web_assets_dir or Path(__file__).parent / 'web_assets'}")
            
            # Start serving requests
            self.server.serve_forever()
            
        except KeyboardInterrupt:
            log.info("\nShutting down the server (user interrupt)...")
            self.stop()

        except Exception as e:
            log.error(f"Error starting server: {e}")
            raise e

    def _configure_https(self) -> None:
        """
        Configure HTTPS/SSL for the web server.
        
        Returns:
            None
        """
        try:
            # Get SSL configuration
            cert_file = self.ssl_config.get('ssl_cert_file')
            key_file = self.ssl_config.get('ssl_key_file')
            cert_chain_file = self.ssl_config.get('ssl_cert_chain_file')
            
            # Validate required SSL files
            if not cert_file or not key_file:
                raise ValueError("SSL certificate file and key file are required for HTTPS")
            
            # Check if files exist
            if not Path(cert_file).exists():
                raise FileNotFoundError(f"SSL certificate file not found: {cert_file}")
            if not Path(key_file).exists():
                raise FileNotFoundError(f"SSL key file not found: {key_file}")
            if cert_chain_file and not Path(cert_chain_file).exists():
                raise FileNotFoundError(f"SSL certificate chain file not found: {cert_chain_file}")
            
            # Create SSL context
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            
            # Configure SSL options
            ssl_verify_mode = self.ssl_config.get('ssl_verify_mode', 'CERT_REQUIRED')
            if ssl_verify_mode == 'CERT_NONE':
                ssl_context.verify_mode = ssl.CERT_NONE
            elif ssl_verify_mode == 'CERT_OPTIONAL':
                ssl_context.verify_mode = ssl.CERT_OPTIONAL
            else:  # CERT_REQUIRED (default)
                ssl_context.verify_mode = ssl.CERT_REQUIRED
            
            # Configure hostname checking
            if not self.ssl_config.get('ssl_check_hostname', True):
                ssl_context.check_hostname = False
            
            # Load certificate and key
            ssl_context.load_cert_chain(cert_file, key_file)
            log.info(f"Loaded SSL certificate: {cert_file} with key: {key_file}")
            
            # Set strong cipher suites (optional, for security)
            try:
                ssl_context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
            except ssl.SSLError:
                # Fall back to default ciphers if custom ones fail
                log.warning("Failed to set custom cipher suites, using defaults")
            
            # Apply SSL context to server socket
            if self.server and hasattr(self.server, 'socket'):
                self.server.socket = ssl_context.wrap_socket(self.server.socket, server_side=True)
            else:
                raise RuntimeError("Server socket not available for SSL configuration")
            
            log.info("HTTPS/SSL configured successfully")
            
        except Exception as e:
            log.error(f"Failed to configure HTTPS/SSL: {e}")
            raise e
    
    def stop(self) -> None:
        """
        Stop the web server.
        
        Returns:
            None
        """
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            log.info("Server stopped.")

    def register_view(self, urls: List[str], template: str, context: Dict[str, Any], process_context: Optional[FunctionType] = None) -> None:
        """
        Register a view to render.
        
        Args:
            urls (List[str]): List of URL patterns
            template (str): Template name to render
            context (Dict[str, Any]): Context data for template
            process_context (Optional[FunctionType]): Optional function to process context
            
        Returns:
            None
        """
        log.info(f"Register view for: {urls}.")
        self.views.append(View(urls=urls, context=context, template=template, process_context=process_context))

    def register_api(self, urls: List[str], callback: Callable[..., Any]) -> None:
        """
        Register an API endpoint.
        
        Args:
            urls (List[str]): List of URL patterns
            callback (Callable[..., Any]): Callback function for the API endpoint
            
        Returns:
            None
        """
        log.info(f"Register API for: {urls}.")
        self.get_apis.append(API(urls=urls, callback=callback))

    def register_post_api(self, urls: List[str], callback: Callable[..., Any]) -> None:
        """
        Register a POST API endpoint.
        
        Args:
            urls (List[str]): List of URL patterns
            callback (Callable[..., Any]): Callback function for the POST API endpoint
            
        Returns:
            None
        """
        log.info(f"Register POST API for: {urls}.")
        self.post_apis.append(API(urls=urls, callback=callback))

