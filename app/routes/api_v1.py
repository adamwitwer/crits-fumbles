"""RESTful API v1 endpoints for external integration"""

from flask import request, jsonify, current_app
from ..utils.validators import validate_roll_payload, ValidationError
from ..utils.exceptions import DiceRollError
from ..services.custom_tables_service import CustomTablesService

def register_api_v1_routes(app, roll_service, data_service, logging_service):
    """Register RESTful API v1 routes"""
    
    custom_tables_service = CustomTablesService()
    
    @app.route('/api/v1/tables', methods=['GET'])
    def get_available_tables():
        """Get all available dice tables"""
        try:
            crit_data = data_service.crit_data
            fumble_data = data_service.fumble_data
            
            tables = {
                "critical_hits": {},
                "fumbles": {},
                "metadata": {
                    "total_crit_sources": len(crit_data),
                    "total_fumble_sources": len(fumble_data)
                }
            }
            
            # Process critical hit tables
            for source, source_data in crit_data.items():
                if source == "effects_tables":
                    continue
                tables["critical_hits"][source] = {
                    "damage_types": list(source_data.keys()),
                    "total_tables": len(source_data)
                }
            
            # Process fumble tables
            for source, source_data in fumble_data.items():
                tables["fumbles"][source] = {
                    "attack_types": list(source_data.keys()),
                    "total_tables": len(source_data)
                }
            
            return jsonify(tables)
            
        except Exception as e:
            current_app.logger.error(f"Error retrieving tables: {e}")
            return jsonify({"error": "Failed to retrieve available tables"}), 500
    
    @app.route('/api/v1/tables/<table_type>/<source>/<table_name>', methods=['GET'])
    def get_specific_table(table_type, source, table_name):
        """Get a specific dice table"""
        try:
            if table_type == "critical":
                data = data_service.crit_data.get(source, {}).get(table_name)
            elif table_type == "fumble":
                data = data_service.fumble_data.get(source, {}).get(table_name)
            else:
                return jsonify({"error": "Invalid table type. Use 'critical' or 'fumble'"}), 400
            
            if not data:
                return jsonify({"error": "Table not found"}), 404
            
            return jsonify({
                "table_type": table_type,
                "source": source,
                "table_name": table_name,
                "data": data
            })
            
        except Exception as e:
            current_app.logger.error(f"Error retrieving table {table_type}/{source}/{table_name}: {e}")
            return jsonify({"error": "Failed to retrieve table"}), 500
    
    @app.route('/api/v1/roll', methods=['POST'])
    def api_roll():
        """API endpoint for rolling dice"""
        try:
            payload = request.get_json()
            if not payload:
                return jsonify({"error": "Invalid JSON payload"}), 400
            
            # Get client IP for geolocation
            xff = request.headers.get('X-Forwarded-For')
            client_ip = xff.split(',')[0].strip() if xff else request.remote_addr
            
            # Process roll
            result = roll_service.process_roll(payload, client_ip)
            
            # Return result with API metadata
            api_response = {
                "api_version": "1.0",
                "timestamp": result.get("timestamp"),
                "roll_result": result
            }
            
            return jsonify(api_response)
            
        except ValidationError as e:
            return jsonify({"error": f"Validation error: {str(e)}"}), 400
        except DiceRollError as e:
            return jsonify({"error": f"Roll error: {str(e)}"}), 400
        except Exception as e:
            current_app.logger.error(f"API roll error: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    @app.route('/api/v1/roll/critical', methods=['POST'])
    def api_roll_critical():
        """Simplified API endpoint for critical hits"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid JSON payload"}), 400
            
            # Build standard payload
            payload = {
                "rollContext": "primary",
                "rollType": "crit",
                "critSource": data.get("source", "Sterling Vermin"),
                "damageType": data.get("damage_type", "slashing"),
                "magicSubtype": data.get("magic_subtype")
            }
            
            # Get client IP
            xff = request.headers.get('X-Forwarded-For')
            client_ip = xff.split(',')[0].strip() if xff else request.remote_addr
            
            result = roll_service.process_roll(payload, client_ip)
            return jsonify(result)
            
        except Exception as e:
            current_app.logger.error(f"API critical roll error: {e}")
            return jsonify({"error": "Critical roll failed"}), 500
    
    @app.route('/api/v1/roll/fumble', methods=['POST'])
    def api_roll_fumble():
        """Simplified API endpoint for fumbles"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid JSON payload"}), 400
            
            # Build standard payload
            payload = {
                "rollContext": "primary",
                "rollType": "fumble",
                "fumbleType": data.get("source", "Questionable Arcana"),
                "attackType": data.get("attack_type", "Weapon")
            }
            
            # Get client IP
            xff = request.headers.get('X-Forwarded-For')
            client_ip = xff.split(',')[0].strip() if xff else request.remote_addr
            
            result = roll_service.process_roll(payload, client_ip)
            return jsonify(result)
            
        except Exception as e:
            current_app.logger.error(f"API fumble roll error: {e}")
            return jsonify({"error": "Fumble roll failed"}), 500
    
    @app.route('/api/v1/cache/stats', methods=['GET'])
    def get_cache_stats():
        """Get caching statistics"""
        try:
            stats = data_service.get_cache_stats()
            return jsonify(stats)
        except Exception as e:
            current_app.logger.error(f"Cache stats error: {e}")
            return jsonify({"error": "Failed to retrieve cache stats"}), 500
    
    @app.route('/api/v1/cache/reload', methods=['POST'])
    def reload_cache():
        """Force reload of data cache"""
        try:
            data_service.reload_data()
            stats = data_service.get_cache_stats()
            return jsonify({"message": "Cache reloaded successfully", "stats": stats})
        except Exception as e:
            current_app.logger.error(f"Cache reload error: {e}")
            return jsonify({"error": "Failed to reload cache"}), 500
    
    @app.route('/api/v1/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        try:
            # Check if critical data can be loaded
            crit_data = data_service.crit_data
            fumble_data = data_service.fumble_data
            
            health_status = {
                "status": "healthy",
                "version": "1.0",
                "data_loaded": {
                    "critical_hits": bool(crit_data),
                    "fumbles": bool(fumble_data)
                },
                "cache_stats": data_service.get_cache_stats()
            }
            
            return jsonify(health_status)
            
        except Exception as e:
            current_app.logger.error(f"Health check error: {e}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e)
            }), 500
    
    # Custom Tables API Endpoints
    @app.route('/api/v1/custom-tables', methods=['GET'])
    def list_custom_tables():
        """List all custom tables"""
        try:
            tables = custom_tables_service.list_tables()
            return jsonify({"tables": tables})
        except Exception as e:
            current_app.logger.error(f"Error listing custom tables: {e}")
            return jsonify({"error": "Failed to list custom tables"}), 500
    
    @app.route('/api/v1/custom-tables', methods=['POST'])
    def create_custom_table():
        """Create a new custom table"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid JSON payload"}), 400
            
            table_name = data.get("name")
            table_type = data.get("type")
            table_data = data.get("data")
            description = data.get("description", "")
            
            if not all([table_name, table_type, table_data]):
                return jsonify({"error": "Missing required fields: name, type, data"}), 400
            
            table = custom_tables_service.create_table(table_name, table_type, table_data, description)
            return jsonify({"message": "Table created successfully", "table": table}), 201
            
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            current_app.logger.error(f"Error creating custom table: {e}")
            return jsonify({"error": "Failed to create table"}), 500
    
    @app.route('/api/v1/custom-tables/<table_name>', methods=['GET'])
    def get_custom_table(table_name):
        """Get a specific custom table"""
        try:
            table = custom_tables_service.get_table(table_name)
            return jsonify({"table": table})
        except ValidationError as e:
            return jsonify({"error": str(e)}), 404
        except Exception as e:
            current_app.logger.error(f"Error retrieving custom table: {e}")
            return jsonify({"error": "Failed to retrieve table"}), 500
    
    @app.route('/api/v1/custom-tables/<table_name>', methods=['PUT'])
    def update_custom_table(table_name):
        """Update a custom table"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid JSON payload"}), 400
            
            table_data = data.get("data")
            description = data.get("description")
            
            table = custom_tables_service.update_table(table_name, table_data, description)
            return jsonify({"message": "Table updated successfully", "table": table})
            
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            current_app.logger.error(f"Error updating custom table: {e}")
            return jsonify({"error": "Failed to update table"}), 500
    
    @app.route('/api/v1/custom-tables/<table_name>', methods=['DELETE'])
    def delete_custom_table(table_name):
        """Delete a custom table"""
        try:
            deleted_table = custom_tables_service.delete_table(table_name)
            return jsonify({"message": "Table deleted successfully", "deleted_table": deleted_table})
        except ValidationError as e:
            return jsonify({"error": str(e)}), 404
        except Exception as e:
            current_app.logger.error(f"Error deleting custom table: {e}")
            return jsonify({"error": "Failed to delete table"}), 500
    
    @app.route('/api/v1/custom-tables/<table_name>/export', methods=['GET'])
    def export_custom_table(table_name):
        """Export a custom table to JSON"""
        try:
            export_data = custom_tables_service.export_table_to_json(table_name)
            return jsonify(export_data)
        except ValidationError as e:
            return jsonify({"error": str(e)}), 404
        except Exception as e:
            current_app.logger.error(f"Error exporting custom table: {e}")
            return jsonify({"error": "Failed to export table"}), 500
    
    @app.route('/api/v1/custom-tables/import', methods=['POST'])
    def import_custom_table():
        """Import a custom table from JSON"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid JSON payload"}), 400
            
            table_name = data.get("name")
            json_data = data.get("table_data", data)
            
            table = custom_tables_service.import_table_from_json(json_data, table_name)
            return jsonify({"message": "Table imported successfully", "table": table}), 201
            
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            current_app.logger.error(f"Error importing custom table: {e}")
            return jsonify({"error": "Failed to import table"}), 500