import logging
from flask import request  
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request 


import logging
from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity


def _safe_get_user():
    """Try to get the current user from JWT without requiring it."""
    try:
        verify_jwt_in_request(optional=True)  # won't raise if no JWT
        return get_jwt_identity()
    except Exception:
        return None

class AppLogger:
    def __init__(self):
        # use a fallback logger immediately, so it's never None
        self.logger = logging.getLogger("app_logger")
        self.logger.addHandler(logging.NullHandler())

    def init_app(self, app):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        )
        self.logger = logging.getLogger("app_logger")
        app.logger = self.logger

    #for signup and login
    def log_auth_attempt(self, email, ip_address):
        self.logger.info(f"Login attempt - Email: {email}, IP: {ip_address}")
    def sign_auth_attempt(self, email, ip_address):
        self.logger.info(f"signup attempt - Email: {email}, ip: {ip_address}")

    #for login and signup
    def log_auth_success(self, email, business_name=None):
        business_info = f" (Business: {business_name})" if business_name else ""
        self.logger.info(f"Login SUCCESS - {email}{business_info}")
    def sign_auth_success(self, email, business_name=None):
        business_info = f"(Business: {business_name})" if business_name else ""
        self.logger.info(f"Signup SUCCESS - {email}{business_info}")

    def log_auth_failure(self, email, reason="Invalid credentials"):
        self.logger.warning(f"Login FAILED - {email} - Reason: {reason}")

    def log_user_action(self, action, details=None):
        current_user = _safe_get_user() or "Anonymous"
        details_str = f" - {details}" if details else ""
        self.logger.info(f"User action: {action} by {current_user}{details_str}")

    def log_business_event(self, event, data=None):
        current_user = _safe_get_user() or "Anonymous"
        data_str = f" - Data: {data}" if data else ""
        self.logger.info(f"Business event: {event} by {current_user}{data_str}")

    def log_error(self, error_msg, exception=None, context=None):
        current_user = _safe_get_user() or "Anonymous"
        context_str = f" - Context: {context}" if context else ""
        if exception:
            self.logger.error(
                f"ERROR for {current_user}: {error_msg}{context_str}", exc_info=True
            )
        else:
            self.logger.error(
                f"ERROR for {current_user}: {error_msg}{context_str}"
            )

    def log_security_event(self, event, details=None):
        ip = request.remote_addr if request else "Unknown IP"
        current_user = _safe_get_user() or "Anonymous"
        details_str = f" - {details}" if details else ""
        self.logger.warning(
            f"SECURITY: {event} by {current_user} from IP: {ip}{details_str}"
        )
