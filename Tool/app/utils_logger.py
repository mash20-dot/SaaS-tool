import logging
from flask import request  
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request 


import logging
from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity


def _safe_get_user():
    """Try to get the current user from JWT without requiring it."""
    try:
        verify_jwt_in_request(optional=True) 
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

    #for posting products
    def product_attempt(self, current_user, ip_address):
        self.logger.info(f"product post attempt: {current_user} added a product, ip: {ip_address}")
    #update product
    def product_update_attempt(self, current_user, ip_address):
        self.logger.info(f"{current_user} attempt to update product, ip:{ip_address}")
    #archive product
    def product_archive_attempt(self, current_user, ip_address):
        self.logger.info(f"{current_user} attempt to archive a product, ip: {ip_address}")
    #product search
    def product_search_attempt(self, current_user, ip_address):
        self.logger.info(f"{current_user} attempt to search for product, ip:{ip_address}")
    #product_status
    def product_status_attempt(self, current_user, ip_address):
        self.logger.info(f"{current_user} tried searching for s product, ip:{ip_address}")



    #for login and signup
    def log_auth_success(self, email, business_name=None):
        business_info = f" (Business: {business_name})" if business_name else ""
        self.logger.info(f"Login SUCCESS - {email}{business_info}")
    def sign_auth_success(self, email, business_name=None):
        business_info = f"(Business: {business_name})" if business_name else ""
        self.logger.info(f"Signup SUCCESS - {email}{business_info}")
    

    #for posting product
    def product_success(self, current_user):
        self.logger.info(f"Product added by {current_user}")
    #update product
    def product_update_success(self, current_user):
        self.logger.info(f"product updated by {current_user}")
    #archive product
    def product_archive_success(self, current_user):
        self.logger.info(f"{current_user} archive a product")
    #product search
    def product_search_success(self, current_user):
        self.logger.info(f"{current_user} searched for a product")
    #product status
    def product_status_success(self, current_user):
        self.logger.info(f"{current_user} searched for a product based on status")



    #for login and signup
    def log_auth_failure(self, email, reason="Invalid credentials"):
        self.logger.warning(f"Login FAILED - {email} - Reason: {reason}")
    def sign_auth_failure(self, email, reason="Empty fields"):
        self.logger.warning(f"Signup FAILED - {email} - Reason: {reason}")

    

    #for posting product
    def product_failure(self, current_user, reason="Missing fields"):
        self.logger.info(f"Failed to add product, {current_user}, Reasons: {reason}")
    #product update
    def product_update_failure(self, current_user, reason="Missing fileds"):
        self.logger.info(f"Failed to update product by {current_user}, Reasons={reason}")
    #product archive
    def product_archive_failure(self, current_user, reason="unauthorized"):
        self.logger.info(f"{current_user} failed to archive a product, Reasons={reason}")
    #product search
    def product_search_failure(self, current_user, reason="missing field"):
        self.logger.info(f"{current_user} failed to search product, Reason={reason}")
    #product status
    def product_status_failure(self, current_user, reason="failed"):
        self.logger.info(f"{current_user}, Reasons={reason}")



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
