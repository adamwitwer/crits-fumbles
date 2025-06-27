"""Logging service for narrative dice roll logging"""

import json
import os
import datetime
import random
from flask import current_app
from ..config import Config

class LoggingService:
    """Service for handling narrative logging of dice rolls"""
    
    def __init__(self, config=None):
        self.config = config or Config()
        self.log_file_path = self._ensure_log_directory()
    
    def _ensure_log_directory(self):
        """Ensure log directory exists and return log file path"""
        try:
            os.makedirs(self.config.LOG_STORAGE_DIR, exist_ok=True)
            log_path = os.path.join(self.config.LOG_STORAGE_DIR, self.config.LOG_FILENAME)
            # Only log if we have an app context
            try:
                current_app.logger.info(f"Log directory ensured/created: {self.config.LOG_STORAGE_DIR}")
                current_app.logger.info(f"Application will use log file at: {log_path}")
            except RuntimeError:
                # No app context yet, that's okay during initialization
                pass
            return log_path
        except OSError as e:
            fallback_path = os.path.join('.', self.config.LOG_FILENAME)
            # Only log if we have an app context
            try:
                current_app.logger.error(f"CRITICAL: Error creating log directory {self.config.LOG_STORAGE_DIR}: {e}. Log persistence may fail.", exc_info=True)
                current_app.logger.warning(f"Falling back to using log file in current directory: '.' due to error with {self.config.LOG_STORAGE_DIR}.")
                current_app.logger.info(f"Fallback log file path is now: {fallback_path}")
            except RuntimeError:
                # No app context yet, that's okay during initialization
                print(f"CRITICAL: Error creating log directory {self.config.LOG_STORAGE_DIR}: {e}. Using fallback: {fallback_path}")
            return fallback_path
    
    def log_successful_roll(self, response, payload, geo_info):
        """Log a successful dice roll with narrative description"""
        try:
            narrative = self._build_narrative(response, payload, geo_info)
            log_entry = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "narrative": narrative,
                "raw_payload": payload,
                "raw_response": response
            }
            
            with open(self.log_file_path, "a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(log_entry) + "\n")
            
            print(f"NARRATIVE LOG: {narrative}")
            
        except Exception as e:
            current_app.logger.error(f"Log write error: {e}", exc_info=True)
            print(f"CRITICAL: Log write fail: {e}")
    
    def _build_narrative(self, response, payload, geo_info):
        """Build narrative description of the roll"""
        descriptor = random.choice(self.config.RANDOM_DESCRIPTORS)
        city = geo_info.get("city", "city?")
        region = geo_info.get("regionName", "region?")
        roll_value = response.get("rollValue")
        
        # Determine table name and result
        table_name, result_log = self._get_table_info(response, payload)
        
        # Format descriptor
        descriptor_words = descriptor.split(' ')
        article = self._get_article(descriptor_words)
        noun = self._get_noun(descriptor_words)
        
        # Build narrative
        narrative = f"{article} {noun} from {city}, {region} rolled {roll_value} on {table_name}, resulting in: \"{str(result_log).strip()}\""
        
        # Add pending secondary roll note
        if response.get("isSecondaryPrompt") and not response.get("secondaryResultText"):
            narrative += " (Bonus roll pending...)"
        
        return narrative
    
    def _get_table_info(self, response, payload):
        """Get table name and result for logging"""
        roll_context = payload.get('rollContext', 'primary')
        roll_type = payload.get('rollType')
        
        if roll_context == 'primary':
            if roll_type == 'crit':
                return self._get_crit_table_info(response, payload)
            elif roll_type == 'fumble':
                return self._get_fumble_table_info(response, payload)
        elif roll_context == 'secondary':
            table_name = f"{roll_type.title()} Effect"
            result_log = response.get("secondaryResultText", "N/A")
            return table_name, result_log
        
        return "Unknown Table", "N/A"
    
    def _get_crit_table_info(self, response, payload):
        """Get critical hit table information"""
        source = response.get("selectedCritSource", "?")
        damage_key = (payload.get('damageType') or "?").lower()
        
        if source == 'Sterling Vermin':
            magic_subtype = payload.get('magicSubtype')
            damage_type = payload.get('damageType')
            damage_key = (magic_subtype if damage_type == 'magic' else damage_type or 'slashing').lower()
        
        table_name = f"{source} Crit ({damage_key.title()})"
        
        # Format result
        description = response.get("description")
        effect = response.get("effect")
        if description and effect:
            result_log = f"{description} Effect: {effect}"
        else:
            result_log = response.get("resultText", "N/A")
        
        return table_name, result_log
    
    def _get_fumble_table_info(self, response, payload):
        """Get fumble table information"""
        source = response.get("selectedFumbleType", "?")
        attack_type = response.get("selectedAttackType", "?")
        
        table_name = f"{source} Fumble ({attack_type.title() if attack_type else 'Unknown'})"
        
        # Format result
        description = response.get("description", "")
        effect = response.get("effect", "")
        if effect:
            result_log = f"{description} Effect: {effect}".strip()
        else:
            result_log = description
        
        return table_name, result_log
    
    def _get_article(self, descriptor_words):
        """Get appropriate article for descriptor"""
        if descriptor_words and descriptor_words[0].lower() in ["a", "an"]:
            return descriptor_words[0].capitalize()
        else:
            first_char = descriptor_words[0][0].lower() if descriptor_words else 'a'
            return "An" if first_char in 'aeiou' else "A"
    
    def _get_noun(self, descriptor_words):
        """Get noun part of descriptor"""
        if descriptor_words and descriptor_words[0].lower() in ["a", "an"]:
            return ' '.join(descriptor_words[1:])
        else:
            return ' '.join(descriptor_words)
    
    def get_roll_history(self, limit=50):
        """Get recent roll history"""
        if not os.path.exists(self.log_file_path):
            return []
        
        try:
            logs = []
            with open(self.log_file_path, "r", encoding="utf-8") as log_file:
                lines = log_file.readlines()
            
            for line in lines[-limit:]:
                try:
                    entry = json.loads(line)
                    logs.append({
                        "timestamp": entry.get("timestamp"),
                        "narrative": entry.get("narrative")
                    })
                except json.JSONDecodeError:
                    continue
            
            # Return most recent first
            return list(reversed([log for log in logs if log.get("narrative")]))
            
        except Exception as e:
            current_app.logger.error(f"History read error: {e}")
            return []