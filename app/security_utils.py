"""
Security utility functions for Crits & Fumbles application.
Handles IP address redaction, rate limiting, and other security concerns.
"""

import ipaddress
import requests
import secrets
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Optional, Tuple
import json


class IPRedactor:
    """Handles IP address privacy and geolocation with consistent redaction."""
    
    REDACTED_PLACEHOLDER = "[IP REDACTED]"
    
    @classmethod
    def classify_ip(cls, ip_address: str) -> Tuple[bool, Dict[str, str]]:
        """
        Classify IP address and return (is_external, location_info).
        
        Args:
            ip_address: The IP address to classify
            
        Returns:
            Tuple of (is_external_ip, location_dict)
        """
        if not ip_address:
            return False, {"city": "an unknown void", "regionName": "the ether"}
        
        try:
            ip_obj = ipaddress.ip_address(ip_address)
            
            if ip_obj.is_loopback:
                return False, {"city": "their cozy terminal", "regionName": "the local machine"}
            
            if ip_obj.is_private:
                return False, {"city": "their local sanctum", "regionName": "the home network"}
            
            # Check for Carrier-Grade NAT (RFC 6598)
            if ip_obj in ipaddress.ip_network('100.64.0.0/10', strict=False):
                return False, {"city": "their secure Tailnet", "regionName": "a private dimension"}
                
            return True, {}
            
        except ValueError:
            # Handle string inputs like "localhost"
            if isinstance(ip_address, str) and ip_address.lower() == "localhost":
                return False, {"city": "their cozy terminal", "regionName": "the local machine"}
            
            return False, {"city": "an unidentifiable nexus", "regionName": "a glitch in the matrix"}
    
    @classmethod
    def get_geolocation(cls, ip_address: str, logger=None) -> Dict[str, str]:
        """
        Get geolocation for IP address with privacy protection.
        
        Args:
            ip_address: The IP address to geolocate
            logger: Optional logger for error reporting
            
        Returns:
            Dictionary with 'city' and 'regionName' keys
        """
        is_external, location_info = cls.classify_ip(ip_address)
        
        if not is_external:
            return location_info
        
        # For external IPs, make API call but redact in logs
        try:
            url = f"http://ip-api.com/json/{ip_address}?fields=status,message,city,regionName,query"
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "success":
                return {
                    "city": data.get("city", "unknown city"), 
                    "regionName": data.get("regionName", "uncharted territory")
                }
            
            # Log error with redacted IP
            api_message = cls._redact_ip_from_message(
                data.get('message', 'Unknown ip-api.com error'), 
                ip_address
            )
            if logger:
                logger.warning(f"Geo API error for {cls.REDACTED_PLACEHOLDER}: {api_message}")
            
            return {"city": "parts unknown", "regionName": "mysterious land"}
            
        except requests.exceptions.Timeout:
            if logger:
                logger.warning(f"Geo request timed out for {cls.REDACTED_PLACEHOLDER}")
            return {"city": "realm beyond reach", "regionName": "mists of time"}
            
        except requests.exceptions.RequestException as e:
            error_message = cls._redact_ip_from_message(str(e), ip_address)
            if logger:
                logger.warning(f"Error fetching geo for {cls.REDACTED_PLACEHOLDER}: {error_message}")
            return {"city": "digital realm", "regionName": "boundless interwebs"}
            
        except json.JSONDecodeError:
            if logger:
                logger.warning(f"Failed to decode geo JSON for {cls.REDACTED_PLACEHOLDER}")
            return {"city": "garbled signal", "regionName": "static void"}
            
        except Exception as e:
            error_message = cls._redact_ip_from_message(str(e), ip_address)
            if logger:
                logger.error(f"Generic geo error for {cls.REDACTED_PLACEHOLDER}: {error_message}", exc_info=True)
            return {"city": "place beyond perception", "regionName": "the void"}
    
    @classmethod
    def _redact_ip_from_message(cls, message: str, ip_address: str) -> str:
        """Remove IP address from error messages for privacy."""
        if isinstance(ip_address, str) and ip_address in message:
            return message.replace(ip_address, cls.REDACTED_PLACEHOLDER)
        return message


class RateLimiter:
    """Simple in-memory rate limiter for API endpoints."""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.last_cleanup = datetime.now()
    
    def is_allowed(self, client_id: str, limit: int = 10, window_minutes: int = 1) -> bool:
        """
        Check if request is allowed under rate limit.
        
        Args:
            client_id: Unique identifier for the client (IP address)
            limit: Maximum requests allowed in time window
            window_minutes: Time window in minutes
            
        Returns:
            True if request is allowed, False if rate limited
        """
        now = datetime.now()
        
        # Cleanup old entries every 5 minutes
        if (now - self.last_cleanup).total_seconds() > 300:
            self._cleanup_old_entries(now, window_minutes)
            self.last_cleanup = now
        
        # Check current client's requests
        client_requests = self.requests[client_id]
        window_start = now - timedelta(minutes=window_minutes)
        
        # Remove requests outside the window
        client_requests[:] = [req_time for req_time in client_requests if req_time > window_start]
        
        # Check if under limit
        if len(client_requests) >= limit:
            return False
        
        # Add current request
        client_requests.append(now)
        return True
    
    def _cleanup_old_entries(self, now: datetime, window_minutes: int):
        """Remove old entries to prevent memory growth."""
        cutoff = now - timedelta(minutes=window_minutes * 2)  # Keep some buffer
        
        for client_id in list(self.requests.keys()):
            self.requests[client_id][:] = [
                req_time for req_time in self.requests[client_id] 
                if req_time > cutoff
            ]
            
            # Remove empty entries
            if not self.requests[client_id]:
                del self.requests[client_id]


class CSRFProtection:
    """Simple CSRF protection for form submissions."""
    
    def __init__(self):
        self.tokens = {}  # In production, use Redis or database
        self.token_lifetime = timedelta(hours=1)
    
    def generate_token(self, session_id: str) -> str:
        """Generate a new CSRF token for the session."""
        token = secrets.token_urlsafe(32)
        self.tokens[session_id] = {
            'token': token,
            'created': datetime.now()
        }
        return token
    
    def validate_token(self, session_id: str, submitted_token: str) -> bool:
        """Validate a submitted CSRF token."""
        if session_id not in self.tokens:
            return False
        
        token_data = self.tokens[session_id]
        
        # Check if token has expired
        if datetime.now() - token_data['created'] > self.token_lifetime:
            del self.tokens[session_id]
            return False
        
        # Compare tokens securely
        return secrets.compare_digest(token_data['token'], submitted_token)
    
    def cleanup_expired_tokens(self):
        """Remove expired tokens from memory."""
        now = datetime.now()
        expired_sessions = [
            session_id for session_id, token_data in self.tokens.items()
            if now - token_data['created'] > self.token_lifetime
        ]
        
        for session_id in expired_sessions:
            del self.tokens[session_id]


class ErrorHandler:
    """Standardized error response handling."""
    
    @staticmethod
    def create_error_response(message: str, status_code: int = 400, error_type: str = "error"):
        """Create a standardized error response."""
        return {
            "status": "error",
            "errorMessage": message,
            "errorType": error_type
        }, status_code
    
    @staticmethod
    def create_success_response(data=None, message: str = "Success"):
        """Create a standardized success response."""
        response = {"status": "success"}
        if data is not None:
            response["data"] = data
        if message != "Success":
            response["message"] = message
        return response


# Global instances
rate_limiter = RateLimiter()
csrf_protection = CSRFProtection()
error_handler = ErrorHandler()