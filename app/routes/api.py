"""API routes for Discord integration, history, and statistics"""

import os
import csv
import json
import requests
from io import StringIO
from flask import request, jsonify, current_app, Response
from ..utils.validators import validate_discord_message
from ..services.statistics_service import StatisticsService

def register_api_routes(app, logging_service):
    """Register API routes"""
    
    stats_service = StatisticsService()
    
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
    
    @app.route('/api/v1/statistics', methods=['GET'])
    def get_statistics():
        """Get roll statistics and analytics"""
        try:
            stats = stats_service.get_statistics_from_log(logging_service)
            return jsonify(stats)
        except Exception as e:
            current_app.logger.error(f"Statistics error: {e}")
            return jsonify({"status": "error", "msg": "Statistics generation failed."}), 500
    
    @app.route('/api/v1/export/history', methods=['GET'])
    def export_history():
        """Export roll history in various formats"""
        format_type = request.args.get('format', 'json').lower()
        
        try:
            # Get raw log data
            log_data = []
            if os.path.exists(logging_service.log_file_path):
                with open(logging_service.log_file_path, "r", encoding="utf-8") as log_file:
                    for line in log_file:
                        try:
                            entry = json.loads(line)
                            log_data.append(entry)
                        except json.JSONDecodeError:
                            continue
            
            if format_type == 'csv':
                return _export_csv(log_data)
            elif format_type == 'json':
                return _export_json(log_data)
            else:
                return jsonify({"status": "error", "msg": "Unsupported format. Use 'json' or 'csv'."}), 400
                
        except Exception as e:
            current_app.logger.error(f"Export error: {e}")
            return jsonify({"status": "error", "msg": "Export failed."}), 500
    
    @app.route('/api/v1/export/statistics', methods=['GET'])
    def export_statistics():
        """Export statistics data"""
        try:
            stats = stats_service.get_statistics_from_log(logging_service)
            response = Response(
                json.dumps(stats, indent=2),
                mimetype='application/json',
                headers={'Content-Disposition': 'attachment; filename=dice_statistics.json'}
            )
            return response
        except Exception as e:
            current_app.logger.error(f"Statistics export error: {e}")
            return jsonify({"status": "error", "msg": "Statistics export failed."}), 500
    
    def _export_csv(log_data):
        """Export log data as CSV"""
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'timestamp', 'narrative', 'roll_type', 'roll_value', 'die_type', 
            'table_used', 'result_description', 'result_effect'
        ])
        
        # Write data
        for entry in log_data:
            response = entry.get('raw_response', {})
            payload = entry.get('raw_payload', {})
            
            # Determine table used
            table_used = "Unknown"
            if payload.get('rollType') == 'crit':
                crit_source = payload.get('critSource', 'Unknown')
                damage_type = payload.get('damageType', 'Unknown')
                table_used = f"{crit_source} Crit ({damage_type})"
            elif payload.get('rollType') == 'fumble':
                fumble_type = payload.get('fumbleType', 'Unknown')
                attack_type = payload.get('attackType', 'Unknown')
                table_used = f"{fumble_type} Fumble ({attack_type})"
            
            writer.writerow([
                entry.get('timestamp', ''),
                entry.get('narrative', ''),
                payload.get('rollType', ''),
                response.get('rollValue', ''),
                response.get('dieType', ''),
                table_used,
                response.get('description', ''),
                response.get('effect', '')
            ])
        
        output.seek(0)
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=dice_history.csv'}
        )
        return response
    
    def _export_json(log_data):
        """Export log data as JSON"""
        response = Response(
            json.dumps(log_data, indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': 'attachment; filename=dice_history.json'}
        )
        return response