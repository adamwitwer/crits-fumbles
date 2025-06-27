"""Main roll processing service"""

from flask import current_app
from .dice_service import DiceService
from .geolocation_service import GeolocationService
from .logging_service import LoggingService
from ..utils.validators import validate_roll_payload
from ..utils.exceptions import ValidationError, DiceRollError

class RollService:
    """Main service for processing roll requests"""
    
    def __init__(self, data_service):
        self.data_service = data_service
        self.dice_service = DiceService(data_service)
        self.geo_service = GeolocationService()
        self.logging_service = LoggingService()
    
    def process_roll(self, payload, client_ip=None):
        """Process a roll request and return response"""
        response = self._build_response_template(payload)
        
        try:
            # Validate input
            validate_roll_payload(payload)
            
            # Get geolocation
            geo_info = self.geo_service.get_geolocation(client_ip)
            
            # Process roll based on context
            roll_context = payload.get('rollContext')
            if roll_context == 'primary':
                response = self._handle_primary_roll(payload, response)
            elif roll_context == 'secondary':
                response = self._handle_secondary_roll(payload, response)
            else:
                response.update({
                    "status": "error", 
                    "errorMessage": f"Invalid roll context: {roll_context}"
                })
            
            # Log successful rolls
            if response["status"] == "success":
                self.logging_service.log_successful_roll(response, payload, geo_info)
                
        except ValidationError as e:
            current_app.logger.warning(f"Validation error: {e}")
            response.update({"status": "error", "errorMessage": str(e)})
        except DiceRollError as e:
            current_app.logger.error(f"Dice roll error: {e}")
            response.update({"status": "error", "errorMessage": str(e)})
        except Exception as e:
            current_app.logger.error(f"Unexpected error processing roll: {e}", exc_info=True)
            response.update({
                "status": "error", 
                "errorMessage": f"An internal error occurred: {str(e)}"
            })
        
        return response
    
    def _build_response_template(self, payload):
        """Build response template with default values"""
        return {
            "status": "success",
            "rollValue": None,
            "resultText": None,
            "description": None,
            "effect": None,
            "isSecondaryPrompt": False,
            "secondaryPromptText": None,
            "secondaryType": None,
            "primaryRollValueForSecondary": payload.get('primaryRollValue'),
            "primaryResultForSecondary": payload.get('primaryResultText'),
            "errorMessage": None,
            "selectedRollType": payload.get('rollType'),
            "selectedCritSource": payload.get('critSource'),
            "selectedFumbleType": payload.get('fumbleType'),
            "selectedAttackType": payload.get('attackType'),
            "numDice": 1,
            "dieType": "d20",
            "original_damageType": payload.get('damageType'),
            "original_magicSubtype": payload.get('magicSubtype')
        }
    
    def _handle_primary_roll(self, payload, response):
        """Handle primary roll (crit or fumble)"""
        roll_type = payload.get('rollType')
        
        if roll_type == 'crit':
            return self._handle_crit_roll(payload, response)
        elif roll_type == 'fumble':
            return self._handle_fumble_roll(payload, response)
        else:
            response.update({
                "status": "error",
                "errorMessage": f"Invalid primary roll type: {roll_type}"
            })
            return response
    
    def _handle_crit_roll(self, payload, response):
        """Handle critical hit roll"""
        crit_source = payload.get('critSource', 'Sterling Vermin')
        damage_type = payload.get('damageType')
        magic_subtype = payload.get('magicSubtype')
        
        try:
            result = self.dice_service.roll_critical_hit(crit_source, damage_type, magic_subtype)
            
            # Update response
            response.update({
                "selectedCritSource": crit_source,
                "dieType": result["die_type"],
                "numDice": result["num_dice"],
                "rollValue": result["roll_value"],
                "resultText": result["result_text"],
                "description": result["description"],
                "effect": result["effect"]
            })
            
            # Check for secondary prompt
            if result["secondary_prompt"]:
                response.update({
                    "isSecondaryPrompt": True,
                    "secondaryPromptText": result["secondary_prompt"]["prompt"],
                    "secondaryType": result["secondary_prompt"]["type"]
                })
            
        except DiceRollError as e:
            response.update({"status": "error", "errorMessage": str(e)})
        
        return response
    
    def _handle_fumble_roll(self, payload, response):
        """Handle fumble roll"""
        fumble_source = payload.get('fumbleType')
        attack_type = payload.get('attackType')
        
        try:
            result = self.dice_service.roll_fumble(fumble_source, attack_type)
            
            # Update response
            response.update({
                "selectedFumbleType": fumble_source,
                "selectedAttackType": attack_type,
                "dieType": result["die_type"],
                "numDice": result["num_dice"],
                "rollValue": result["roll_value"],
                "description": result["description"],
                "effect": result["effect"]
            })
            
        except DiceRollError as e:
            response.update({"status": "error", "errorMessage": str(e)})
        
        return response
    
    def _handle_secondary_roll(self, payload, response):
        """Handle secondary roll (injuries, insanity)"""
        roll_type = payload.get('rollType')
        
        try:
            result = self.dice_service.roll_secondary_effect(roll_type)
            
            # Update response
            response.update({
                "dieType": result["die_type"],
                "numDice": result["num_dice"],
                "rollValue": result["roll_value"],
                "secondaryResultText": result["result_text"]
            })
            
        except DiceRollError as e:
            response.update({"status": "error", "errorMessage": str(e)})
        
        return response