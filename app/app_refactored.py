"""
Refactored Flask application for D&D Crits & Fumbles
"""

from flask import Flask
from .config import Config
from .services.data_service import DataService
from .services.roll_service import RollService
from .services.logging_service import LoggingService
from .routes.main import register_main_routes
from .routes.api import register_api_routes
from .routes.api_v1 import register_api_v1_routes

def create_app(config_class=Config):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize services
    data_service = DataService()
    roll_service = RollService(data_service)
    logging_service = LoggingService(config_class)
    
    # Register security headers
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses"""
        response.headers['Content-Security-Policy'] = config_class.CSP_POLICY
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response
    
    # Register routes
    register_main_routes(app, roll_service)
    register_api_routes(app, logging_service)
    register_api_v1_routes(app, roll_service, data_service, logging_service)
    
    return app

# For backwards compatibility and direct running
app = create_app()

if __name__ == '__main__':
    app.run()