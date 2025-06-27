"""Geolocation service for IP address resolution"""

import requests
import json
import ipaddress
from flask import current_app
from ..utils.exceptions import GeolocationError

class GeolocationService:
    """Service for resolving IP addresses to geographical locations"""
    
    def __init__(self):
        self.api_timeout = 3
        self.api_url = "http://ip-api.com/json/"
    
    def get_geolocation(self, ip_address):
        """Get geolocation information for an IP address"""
        # This is the actual IP address used for the geolocation API call
        actual_ip_for_api = ip_address 
        
        # This is the placeholder used for ALL logging messages to avoid sensitive data
        ip_display_for_logs = "[IP REDACTED]"
        
        if not actual_ip_for_api:
            current_app.logger.debug("No IP address provided for geolocation.")
            return {"city": "an unknown void", "regionName": "the ether"}
        
        try:
            return self._resolve_special_ips(actual_ip_for_api, ip_display_for_logs)
        except ValueError:
            # Handle cases like "localhost" string which is not a valid IP for ipaddress module
            if isinstance(actual_ip_for_api, str) and actual_ip_for_api.lower() == "localhost":
                return {"city": "their cozy terminal", "regionName": "the local machine"}
            
            # Log with the placeholder instead of the actual potentially invalid IP string
            current_app.logger.warning(f"Invalid IP format for geolocation: {ip_display_for_logs}")
            return {"city": "an unidentifiable nexus", "regionName": "a glitch in the matrix"}
        
        # For external API calls, the actual ip_address is still used
        return self._query_external_api(actual_ip_for_api, ip_display_for_logs)
    
    def _resolve_special_ips(self, ip_address, ip_display):
        """Resolve special IP addresses (loopback, private, etc.)"""
        ip_obj = ipaddress.ip_address(ip_address)
        
        if ip_obj.is_loopback:
            return {"city": "their cozy terminal", "regionName": "the local machine"}
        
        if ip_obj.is_private:
            return {"city": "their local sanctum", "regionName": "the home network"}
        
        if ip_obj in ipaddress.ip_network('100.64.0.0/10', strict=False):
            return {"city": "their secure Tailnet", "regionName": "a private dimension"}
        
        # If we get here, it's a public IP that needs external API resolution
        raise GeolocationError("Public IP requires external API")
    
    def _query_external_api(self, ip_address, ip_display):
        """Query external geolocation API"""
        try:
            url = f"{self.api_url}{ip_address}?fields=status,message,city,regionName,query"
            response_geo = requests.get(url, timeout=self.api_timeout)
            response_geo.raise_for_status()
            data = response_geo.json()
            
            return self._process_api_response(data, ip_address, ip_display)
            
        except requests.exceptions.Timeout:
            current_app.logger.warning(f"Geo request timed out for {ip_display}")
            return {"city": "realm beyond reach", "regionName": "mists of time"}
        
        except requests.exceptions.RequestException as e:
            error_message = self._sanitize_error_message(str(e), ip_address, ip_display)
            current_app.logger.warning(f"Error fetching geo for {ip_display}: {error_message}")
            return {"city": "digital realm", "regionName": "boundless interwebs"}
        
        except json.JSONDecodeError:
            current_app.logger.warning(f"Failed to decode geo JSON for {ip_display}")
            return {"city": "garbled signal", "regionName": "static void"}
        
        except Exception as e:
            error_message = self._sanitize_error_message(str(e), ip_address, ip_display)
            current_app.logger.error(f"Generic geo error for {ip_display}: {error_message}", exc_info=True)
            return {"city": "place beyond perception", "regionName": "the void"}
    
    def _process_api_response(self, data, ip_address, ip_display):
        """Process the API response and sanitize any IP addresses"""
        api_message = data.get('message', 'Unknown ip-api.com error')
        
        # Sanitize api_message if it might contain the IP
        if data.get("query") and isinstance(api_message, str) and data.get("query") in api_message:
            api_message = api_message.replace(data.get("query"), ip_display)
        
        if data.get("status") == "success":
            return {
                "city": data.get("city", "unknown city"), 
                "regionName": data.get("regionName", "uncharted territory")
            }
        
        # Log error with redacted IP
        current_app.logger.warning(f"Geo API error for {ip_display}: {api_message}")
        return {"city": "parts unknown", "regionName": "mysterious land"}
    
    def _sanitize_error_message(self, error_message, ip_address, ip_display):
        """Remove IP address from error messages"""
        if isinstance(ip_address, str) and ip_address in error_message:
            return error_message.replace(ip_address, ip_display)
        return error_message