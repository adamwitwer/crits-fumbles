"""Main routes for the dice rolling application"""

from flask import render_template, request, jsonify
from ..services.data_service import DataService

def register_main_routes(app, roll_service):
    """Register main application routes"""
    
    @app.route('/', methods=['GET'])
    def index():
        """Main application page"""
        data_service = DataService()
        sv_tables = data_service.crit_data.get('Sterling Vermin', {})
        damage_types = sorted([k for k in sv_tables.keys() if not k.startswith('magic:')])
        magic_subtypes = sorted([k for k in sv_tables.keys() if k.startswith('magic:')])
        
        return render_template(
            'index.html',
            damage_types=damage_types,
            magic_subtypes=magic_subtypes,
            selected_damage_type="slashing",
            selected_roll_type="crit",
            selected_crit_source="Sterling Vermin",
            selected_fumble_type="Questionable Arcana",
            selected_attack_type="Weapon"
        )
    
    @app.route('/roll', methods=['POST'])
    def roll_ajax():
        """Handle dice roll requests"""
        payload = request.get_json()
        print(f"Roll payload: {payload}")
        
        if not payload:
            return jsonify({"status": "error", "errorMessage": "Invalid request data."}), 400
        
        # Extract client IP
        xff = request.headers.get('X-Forwarded-For')
        client_ip = xff.split(',')[0].strip() if xff else request.remote_addr
        
        # Process roll
        result = roll_service.process_roll(payload, client_ip)
        return jsonify(result)