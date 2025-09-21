import logging  # Python's built-in logging library
from flask import request  # To get request info (IP, method, etc.)
from flask_jwt_extended import get_jwt_identity  # To get current user

class AppLogger:
    """
    A class to handle all logging in your application.
    Think of this as your logging assistant - it knows how to log different types of events.
    """
    
    def __init__(self):
        # Create a logger instance for this app
        # __name__ will be something like 'utils.logger'
        self.logger = logging.getLogger('app_logger')
    
    def log_auth_attempt(self, email, ip_address):
        """
        Log when someone tries to login.
        
        Args:
            email: The email they're trying to login with
            ip_address: Where the request came from (security tracking)
        """
        # Log at INFO level - this is normal business activity
        # The 🔐 emoji helps you quickly spot auth events in logs
        self.logger.info(f"🔐 Login attempt - Email: {email}, IP: {ip_address}")
    
    def log_auth_success(self, email, business_name=None):
        """
        Log when someone successfully logs in.
        
        Args:
            email: Who logged in
            business_name: Their business name (optional)
        """
        # Add business name if provided, otherwise just show email
        business_info = f" (Business: {business_name})" if business_name else ""
        # ✅ emoji makes success easy to spot
        self.logger.info(f"✅ Login SUCCESS - {email}{business_info}")
    
    def log_auth_failure(self, email, reason="Invalid credentials"):
        """
        Log when login fails.
        
        Args:
            email: Who tried to login
            reason: Why it failed (wrong password, user not found, etc.)
        """
        # WARNING level because failed logins might indicate attacks
        # ❌ emoji makes failures easy to spot
        self.logger.warning(f"❌ Login FAILED - {email} - Reason: {reason}")
    
    def log_user_action(self, action, details=None):
        """
        Log general things users do (create product, update profile, etc.).
        
        Args:
            action: What they did ("created_product", "updated_profile")
            details: Extra info about the action
        """
        try:
            # Try to get who's currently logged in
            current_user = get_jwt_identity()  # Returns email from JWT token
            # Add details if provided
            details_str = f" - {details}" if details else ""
            # 👤 emoji for user actions
            self.logger.info(f"👤 User action: {action} by {current_user}{details_str}")
        except:
            # If we can't get current user (maybe not logged in), log anyway
            details_str = f" - {details}" if details else ""
            self.logger.info(f"👤 User action: {action}{details_str}")
    
    def log_business_event(self, event, data=None):
        """
        Log important business events (product created, sale made, etc.).
        These are events you might want to analyze for business intelligence.
        
        Args:
            event: What business event happened
            data: Additional data about the event
        """
        try:
            # Get current user
            current_user = get_jwt_identity()
            # Convert data to string if provided
            data_str = f" - Data: {data}" if data else ""
            # 💼 emoji for business events
            self.logger.info(f"💼 Business event: {event} by {current_user}{data_str}")
        except:
            # Log even if no user context
            data_str = f" - Data: {data}" if data else ""
            self.logger.info(f"💼 Business event: {event}{data_str}")
    
    def log_error(self, error_msg, exception=None, context=None):
        """
        Log when something goes wrong.
        
        Args:
            error_msg: Description of what went wrong
            exception: The actual error object (optional)
            context: Extra info about where/why it happened
        """
        try:
            # Get current user if available
            current_user = get_jwt_identity()
            # Add context if provided
            context_str = f" - Context: {context}" if context else ""
            
            if exception:
                # If we have the actual exception, log with full stack trace
                # exc_info=True includes the full error details
                self.logger.error(f"💥 ERROR for {current_user}: {error_msg}{context_str}", exc_info=True)
            else:
                # Just log the error message
                self.logger.error(f"💥 ERROR for {current_user}: {error_msg}{context_str}")
        except:
            # If we can't get user info, still log the error
            context_str = f" - Context: {context}" if context else ""
            if exception:
                self.logger.error(f"💥 ERROR: {error_msg}{context_str}", exc_info=True)
            else:
                self.logger.error(f"💥 ERROR: {error_msg}{context_str}")
    
    def log_security_event(self, event, details=None):
        """
        Log security-related events (failed logins, suspicious activity, etc.).
        These are logged as WARNING because they need attention.
        
        Args:
            event: What security event happened
            details: Additional details about the event
        """
        # Try to get IP address from current request
        ip = request.remote_addr if request else "Unknown IP"
        details_str = f" - {details}" if details else ""
        # 🚨 emoji for security events - these need attention!
        self.logger.warning(f"🚨 SECURITY: {event} from IP: {ip}{details_str}")

# Create one instance that your whole app can use
# This is like creating your logging assistant
app_logger = AppLogger()

# =======================
# HOW TO USE IN YOUR ROUTES
# =======================
