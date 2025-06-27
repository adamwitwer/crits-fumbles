"""API routes for Discord integration and history"""

import os
import requests
from flask import request, jsonify, current_app
from ..utils.validators import validate_discord_message

def register_api_routes(app, logging_service):
    """Register API routes"""
    
    @app.route('/share_discord', methods=['POST'])
    def share_discord():
        """Share roll result to Discord"""
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            return jsonify({"status": "error", "error": "Webhook URL not configured."}), 500
        
        payload = request.get_json()
        message = payload.get('message') if payload else None
        
        if not message:
            return jsonify({"status": "error", "error": "No message content."}), 400
        
        try:
            validate_discord_message(message)
            requests.post(webhook_url, json={'content': message}).raise_for_status()
            return jsonify({"status": "success"})
        except Exception as e:
            current_app.logger.error(f"Discord send error: {e}")
            return jsonify({"status": "error", "error": str(e)}), 500
    
    @app.route('/get_roll_history', methods=['GET'])
    def get_roll_history():
        """Get roll history"""
        try:
            history = logging_service.get_roll_history()
            return jsonify(history)
        except Exception as e:
            current_app.logger.error(f"History retrieval error: {e}")
            return jsonify({"status": "error", "msg": "History retrieval failed."}), 500