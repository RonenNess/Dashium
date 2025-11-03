"""
Basic Authentication Manager.
Author: Ronen Ness.
Created: 2025.
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import logger
import timer

log = logger.get_logger("auth")


class User:
    """
    Represents a user with username and hashed password.
    """
    
    def __init__(self, username: str, hashed_password: str) -> None:
        """
        Initialize a User object.
        
        Args:
            username (str): The username
            hashed_password (str): The hashed password
            
        Returns:
            None
        """
        self.username = username
        self.hashed_password = hashed_password


class Session:
    """
    Represents a user session with access tracking.
    """
    _next_session_debug_id = 1
    
    def __init__(self, user: User, session_id: str) -> None:
        """
        Initialize a Session object.
        
        Args:
            user (User): The authenticated user
            session_id (str): The session identifier
            
        Returns:
            None
        """
        self.user = user
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_access = datetime.now()
        self.debug_id = Session._next_session_debug_id
        Session._next_session_debug_id += 1

    def update_access(self) -> None:
        """
        Update the last access time for this session.
        
        Returns:
            None
        """
        self.last_access = datetime.now()


class AuthenticationManager:
    """
    Basic authentication manager with user management, sessions, and brute force protection.
    """
    
    def __init__(self, session_timeout_hours: int = 24, lock_after_failed_attempts: int = 10, lock_after_failed_attempts_time_minutes: int = 30) -> None:
        """
        Initialize the authentication manager.
        
        Args:
            session_timeout_hours (int): Hours after which inactive sessions expire (default: 24)
            lock_after_failed_attempts (int): Number of failed login attempts before locking the account (default: 10)
            lock_after_failed_attempts_time_minutes (int): Minutes to lock the account after too many failed attempts (default: 30)

        Returns:
            None
        """
        self.users: List[User] = []
        self.sessions: Dict[str, Session] = {}
        self.failed_attempts = 0
        self.lock_until: Optional[datetime] = None
        self.session_timeout_hours = session_timeout_hours
        self.lock_after_failed_attempts = lock_after_failed_attempts
        self.lock_after_failed_attempts_time_minutes = lock_after_failed_attempts_time_minutes

        # Start the session cleanup timer (convert hours to minutes)
        timer.register_timer(self._cleanup_sessions, 30)
        log.info(f"Authentication manager initialized with {session_timeout_hours}h session timeout")
    
    def _hash_password(self, password: str) -> str:
        """
        Hash a password using SHA-256.
        
        Args:
            password (str): Raw password to hash
            
        Returns:
            str: Hashed password
        """
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def _generate_session_id(self) -> str:
        """
        Generate a secure random session ID.
        
        Returns:
            str: Random session ID
        """
        return secrets.token_urlsafe(32)
    
    def create_user(self, username: str, raw_password: str) -> bool:
        """
        Create a new user with username and password.
        
        Args:
            username (str): The username
            raw_password (str): The raw password (will be hashed)
            
        Returns:
            bool: True if user was created successfully, False if username already exists
        """
        # Check if username already exists
        for user in self.users:
            if user.username == username:
                log.warning(f"Attempted to create user '{username}' but username already exists")
                return False
        
        # Create new user with hashed password
        hashed_password = self._hash_password(raw_password)
        new_user = User(username, hashed_password)
        self.users.append(new_user)
        
        log.info(f"Created new user: {username}")
        return True
    
    def is_locked(self) -> bool:
        """
        Check if the authentication manager is currently locked due to failed attempts.
        
        Returns:
            bool: True if locked, False otherwise
        """
        if self.lock_until is None:
            return False
        
        if datetime.now() >= self.lock_until:
            # Lock has expired
            self.lock_until = None
            self.failed_attempts = 0
            log.info("Authentication lock has expired, resetting failed attempts")
            return False
        
        return True

    def authenticate(self, username: str, password: str, password_is_hashed: bool = True) -> Optional[Tuple[User, str]]:
        """
        Authenticate a user with username and password.
        
        Args:
            username (str): The username
            password (str): The raw or hashed password
            password_is_hashed (bool): True if the provided password is already hashed, False if raw (default: True)
            
        Returns:
            Optional[Tuple[User, str]]: Tuple of (User, session_id) if successful, None if failed
        """
        # Check if manager is locked
        if self.is_locked():
            log.warning(f"Authentication attempt for '{username}' rejected - manager is locked")
            return None
        
        # Hash the provided password
        hashed_password = password if password_is_hashed else self._hash_password(password)
        
        # Find user and check password
        for user in self.users:
            if user.username == username and user.hashed_password == hashed_password:
                # Authentication successful
                session_id = self._generate_session_id()
                session = Session(user, session_id)
                self.sessions[session_id] = session
                
                # Reset failed attempts on successful login
                self.failed_attempts = 0
                
                log.info(f"User '{username}' authenticated successfully with session {session_id}")
                return user, session_id
        
        # Authentication failed
        self.failed_attempts += 1
        log.warning(f"Authentication failed for '{username}' (attempt {self.failed_attempts}/10)")
        
        # Check if we should lock the manager
        if self.failed_attempts >= self.lock_after_failed_attempts:
            self.lock_until = datetime.now() + timedelta(minutes=self.lock_after_failed_attempts_time_minutes)
            log.error(f"Authentication manager locked for {self.lock_after_failed_attempts_time_minutes} minutes due to {self.failed_attempts} failed attempts")

        return None
    
    def get_active_sessions_info(self) -> List[Dict[str, str]]:
        """
        Get information about currently active sessions.
        
        Returns:
            List[Dict[str, str]]: List of active sessions with username and session ID
        """
        active_sessions = []
        for session_id, session in self.sessions.items():
            active_sessions.append({
                "username": session.user.username,
                "debug_id": session.debug_id,
                "created_at": session.created_at.isoformat(),
                "last_active_at": session.last_access.isoformat()
            })
        return active_sessions
    
    def retrieve_user_by_session_id(self, session_id: str) -> Optional[User]:
        """
        Retrieve a logged-in user by session ID.
        
        Args:
            session_id (str): The session ID
            
        Returns:
            Optional[User]: The user if session exists and is valid, None otherwise
        """
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check if session has expired
        if datetime.now() - session.last_access > timedelta(hours=self.session_timeout_hours):
            # Session expired, remove it
            del self.sessions[session_id]
            log.info(f"Session {session_id} expired and was removed")
            return None
        
        # Update last access time
        session.update_access()
        return session.user
    
    def logout(self, session_id: str) -> bool:
        """
        Logout a user by removing their session.
        
        Args:
            session_id (str): The session ID to remove
            
        Returns:
            bool: True if session was found and removed, False otherwise
        """
        if session_id in self.sessions:
            username = self.sessions[session_id].user.username
            del self.sessions[session_id]
            log.info(f"User '{username}' logged out, session {session_id} removed")
            return True
        return False
    
    def _cleanup_sessions(self) -> None:
        """
        Clean up expired sessions. Called periodically by timer.
        
        Returns:
            None
        """
        now = datetime.now()
        expired_sessions = []

        self.failed_attempts = 0  # Reset failed attempts during cleanup
        
        for session_id, session in self.sessions.items():
            if now - session.last_access > timedelta(hours=self.session_timeout_hours):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            username = self.sessions[session_id].user.username
            del self.sessions[session_id]
            log.info(f"Cleaned up expired session {session_id} for user '{username}'")
        
        if expired_sessions:
            log.info(f"Session cleanup completed: removed {len(expired_sessions)} expired sessions")
    
    def get_active_sessions_count(self) -> int:
        """
        Get the number of currently active sessions.
        
        Returns:
            int: Number of active sessions
        """
        return len(self.sessions)
    
    def get_user_count(self) -> int:
        """
        Get the total number of registered users.
        
        Returns:
            int: Number of registered users
        """
        return len(self.users)


# Global authentication manager instance
_auth_manager: Optional[AuthenticationManager] = None


def init_auth_manager(session_timeout_hours: int = 24, lock_after_failed_attempts: int = 10, lock_after_failed_attempts_time_minutes: int = 30) -> AuthenticationManager:
    """
    Init the global authentication manager instance (singleton pattern).
    
    Args:
        session_timeout_hours (int): Hours after which inactive sessions expire (default: 24)
        lock_after_failed_attempts (int): Number of failed login attempts before locking the account (default: 10)
        lock_after_failed_attempts_time_minutes (int): Minutes to lock the account after too many failed attempts (default: 30)
        
    Returns:
        AuthenticationManager: The global authentication manager instance
    """
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthenticationManager(session_timeout_hours, lock_after_failed_attempts, lock_after_failed_attempts_time_minutes)
    else:
        raise Exception("Authentication manager is already initialized")
    return _auth_manager


def get_auth_manager() -> AuthenticationManager:
    """
    Get the global authentication manager instance.
    """
    global _auth_manager
    if _auth_manager is None:
        raise Exception("Authentication manager is not initialized. Call init_auth_manager() first.")
    return _auth_manager