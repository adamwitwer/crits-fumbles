"""Dice rolling service for critical hits and fumbles"""

import random
from flask import current_app
from ..utils.exceptions import InvalidTableError, InvalidRollValueError

class DiceService:
    """Service for handling dice rolls and result resolution"""
    
    def __init__(self, data_service):
        self.data_service = data_service
    
    def resolve_roll(self, roll_value, table):
        """Resolve a roll value against a table"""
        if not isinstance(table, dict):
            current_app.logger.warning(f"Invalid table to resolve_roll: {type(table)}")
            raise InvalidTableError(f"Invalid table data: {type(table)}")
        
        try:
            val = int(roll_value)
            for key, result_text in table.items():
                if '-' in key:
                    start, end = map(int, key.split('-'))
                    condition = start <= val <= end
                else:
                    condition = str(val) == key
                
                if condition:
                    return result_text
        except (ValueError, TypeError) as e:
            current_app.logger.error(f"Error resolving roll {roll_value}: {e}", exc_info=True)
            raise InvalidRollValueError(f"Invalid roll value: {roll_value}") from e
        
        # No match found
        table_preview = str(table)[:200] + '...' if len(str(table)) > 200 else str(table)
        current_app.logger.warning(f"No result for roll {roll_value} in table {table_preview}")
        raise InvalidRollValueError(f"No result found for roll {roll_value} in the table")
    
    def roll_critical_hit(self, crit_source, damage_type, magic_subtype=None):
        """Roll for critical hit"""
        crit_data = self.data_service.crit_data
        
        # Determine die type and roll value
        if crit_source in ["Questionable Arcana", "BCoydog"]:
            die_type, num_dice, roll_value = "d100", 1, random.randint(1, 100)
        else:  # Sterling Vermin
            die_type, num_dice, roll_value = "d20", 1, random.randint(1, 20)
        
        # Determine damage key
        crit_damage_key = self._get_crit_damage_key(crit_source, damage_type, magic_subtype)
        
        # Get source tables
        source_tables = crit_data.get(crit_source, {})
        if not source_tables:
            raise InvalidTableError(f"Invalid crit source: {crit_source}")
        
        # Get specific table
        table_data = source_tables.get(crit_damage_key)
        if not table_data:
            raise InvalidTableError(f"Invalid damage type '{crit_damage_key}' for {crit_source} crits")
        
        # Resolve roll
        result_text = self.resolve_roll(roll_value, table_data)
        
        # Parse result based on source
        description, effect = self._parse_crit_result(crit_source, result_text)
        
        # Check for secondary effects
        secondary_prompt = self._check_secondary_effects(result_text)
        
        return {
            "die_type": die_type,
            "num_dice": num_dice,
            "roll_value": roll_value,
            "result_text": result_text if crit_source == "Sterling Vermin" else None,
            "description": description,
            "effect": effect,
            "secondary_prompt": secondary_prompt
        }
    
    def roll_fumble(self, fumble_source, attack_type):
        """Roll for fumble"""
        fumble_data = self.data_service.fumble_data
        
        die_type, num_dice, roll_value = "d100", 1, random.randint(1, 100)
        
        # Get source tables
        fumble_src_tables = fumble_data.get(fumble_source, {})
        if not fumble_src_tables:
            raise InvalidTableError(f"Invalid fumble source: {fumble_source}")
        
        # Determine key to use
        key_to_use = self._get_fumble_key(fumble_source, attack_type)
        
        # Get fumble list
        f_list = fumble_src_tables.get(key_to_use, [])
        
        # Fallback logic for BCoydog
        if not f_list and fumble_source == 'BCoydog':
            general_fumbles = fumble_src_tables.get('general', [])
            if general_fumbles:
                current_app.logger.info(f"Fumble key '{key_to_use}' for BCoydog resulted in empty list. Falling back to 'general' fumbles.")
                f_list = general_fumbles
                key_to_use = 'general'
        
        if not f_list:
            raise InvalidTableError(f"No fumble entries for {fumble_source} - {key_to_use}")
        
        # Find matching entry
        description, effect = self._resolve_fumble_entry(f_list, roll_value, fumble_source, key_to_use)
        
        return {
            "die_type": die_type,
            "num_dice": num_dice,
            "roll_value": roll_value,
            "description": description,
            "effect": effect
        }
    
    def roll_secondary_effect(self, effect_type):
        """Roll for secondary effects (injuries, insanity)"""
        crit_data = self.data_service.crit_data
        
        die_type, num_dice, roll_value = "d20", 1, random.randint(1, 20)
        
        sec_map = {'minor': 'minor_injuries', 'major': 'major_injuries', 'insanity': 'insanities'}
        sec_key = sec_map.get(effect_type)
        
        if not sec_key:
            raise InvalidTableError(f"Invalid secondary effect type: {effect_type}")
        
        eff_data = crit_data.get('effects_tables', {}).get(sec_key, {})
        if not eff_data:
            raise InvalidTableError(f"Secondary table '{sec_key}' not found")
        
        result_text = self.resolve_roll(roll_value, eff_data)
        
        return {
            "die_type": die_type,
            "num_dice": num_dice,
            "roll_value": roll_value,
            "result_text": result_text
        }
    
    def _get_crit_damage_key(self, crit_source, damage_type, magic_subtype):
        """Get the damage key for critical hit tables"""
        if crit_source == 'Sterling Vermin':
            if damage_type == 'magic':
                return (magic_subtype.lower().strip() if magic_subtype else 'slashing')
            return (damage_type.lower().strip() if damage_type else 'slashing')
        else:
            return (damage_type.lower().strip() if damage_type else None)
    
    def _get_fumble_key(self, fumble_source, attack_type):
        """Get the key for fumble tables"""
        if fumble_source == 'Questionable Arcana':
            # QA expects 'Weapon' or 'Magic' from frontend for attack_type
            return "Weapon Attack" if attack_type == 'Weapon' else "Spell Attack"
        elif fumble_source == 'BCoydog':
            # BCoydog receives 'melee', 'ranged', or 'magic' (lowercase) from frontend
            key_to_use = attack_type.lower() if attack_type else None
            if key_to_use not in ['melee', 'ranged', 'magic']:
                current_app.logger.warning(f"Received unexpected attack_type '{attack_type}' for BCoydog fumble. Defaulting to general or error.")
            return key_to_use
        else:
            raise InvalidTableError(f"Fumble logic not defined for source: {fumble_source}")
    
    def _parse_crit_result(self, crit_source, result_text):
        """Parse critical hit result text based on source"""
        if crit_source == "Questionable Arcana" and isinstance(result_text, str):
            parts = result_text.split(" Effect: ", 1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
            return result_text, "Details not separated."
        
        elif crit_source == "BCoydog" and isinstance(result_text, str):
            parts = result_text.split(": ", 1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
            return result_text, "Details not separated."
        
        # Sterling Vermin - return as is
        return None, None
    
    def _check_secondary_effects(self, result_text):
        """Check if result text triggers secondary effects"""
        if not isinstance(result_text, str):
            return None
        
        text_lower = result_text.lower()
        if "minor injury" in text_lower:
            return {"type": "minor", "prompt": "Minor Injury!"}
        elif "major injury" in text_lower:
            return {"type": "major", "prompt": "Major Injury!"}
        elif "insanity" in text_lower:
            return {"type": "insanity", "prompt": "Insanity!"}
        
        return None
    
    def _resolve_fumble_entry(self, f_list, roll_value, fumble_source, key_to_use):
        """Resolve fumble entry from list"""
        for entry in f_list:
            roll_range = entry.get('roll')
            if not roll_range:
                continue
            
            try:
                if '-' in roll_range:
                    low, high = map(int, roll_range.split('-'))
                    match = low <= roll_value <= high
                else:
                    match = int(roll_range) == roll_value
            except ValueError:
                current_app.logger.warning(f"Malformed roll '{roll_range}' in {fumble_source}")
                continue
            
            if match:
                return entry.get('description', 'N/A'), entry.get('effect', 'N/A')
        
        # No match found
        return (
            f"No matching {fumble_source} fumble for {roll_value} in {key_to_use}.",
            "No additional effect."
        )