from dotenv import load_dotenv
load_dotenv()

import requests
import os
import json
import random
from flask import Flask, render_template, request, jsonify, url_for
import datetime
import sys
import os
sys.path.append(os.path.dirname(__file__))
from security_utils import IPRedactor, rate_limiter, csrf_protection, error_handler

app = Flask(__name__)

@app.after_request
def add_security_headers(response):
    csp_policy = (
        "default-src 'none';"
        "script-src 'self' 'sha256-xkCWla5qon65vOIHCOs7ZCr8zHIHr0UgJN5eX5r7PXU=';"
        "style-src 'self' 'unsafe-inline';"
        "img-src 'self' data:;"
        "media-src 'self';"
        "font-src 'self';"
        "connect-src 'self' http://ip-api.com;"
        "form-action 'self';"
        "frame-ancestors 'none';"
        "base-uri 'self';"
        "object-src 'none';"
        "worker-src 'self';"
        "manifest-src 'self';"
    )
    response.headers['Content-Security-Policy'] = csp_policy
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# --- Determine log file path ---
LOG_STORAGE_DIR = os.environ.get('LOG_STORAGE_DIR', '.')
LOG_FILENAME = "narrative_dice_log.jsonl"
NARRATIVE_LOG_FILE_PATH = os.path.join(LOG_STORAGE_DIR, LOG_FILENAME)

# --- Ensure the log directory exists ---
try:
    os.makedirs(LOG_STORAGE_DIR, exist_ok=True)
    app.logger.info(f"Log directory ensured/created: {LOG_STORAGE_DIR}")
    app.logger.info(f"Application will use log file at: {NARRATIVE_LOG_FILE_PATH}")
except OSError as e:
    app.logger.error(f"CRITICAL: Error creating log directory {LOG_STORAGE_DIR}: {e}. Log persistence may fail.", exc_info=True)
    app.logger.warning(f"Falling back to using log file in current directory: '.' due to error with {LOG_STORAGE_DIR}.")
    NARRATIVE_LOG_FILE_PATH = os.path.join('.', LOG_FILENAME)
    app.logger.info(f"Fallback log file path is now: {NARRATIVE_LOG_FILE_PATH}")

# --- Lists for Narrative Logging ---
RANDOM_DESCRIPTORS = [
    "an intrepid adventurer", "a curious scholar", "a daring rogue",
    "a wise wizard", "a valiant knight", "a mysterious stranger",
    "a lucky gambler", "an unfortunate soul", "a cautious traveler",
    "a brave hero", "a cunning strategist", "a wandering minstrel",
    "a forgotten deity", "a mischievous sprite", "a stoic guardian"
]

# --- Load Data ---
def load_json(filename):
    json_path = os.path.join(os.path.dirname(__file__), filename)
    try:
        with open(json_path) as f:
            return json.load(f)
    except FileNotFoundError:
        app.logger.error(f"Error: JSON file not found at {json_path}")
        return {}
    except json.JSONDecodeError:
        app.logger.error(f"Error: Could not decode JSON from {json_path}")
        return {}

# Load data files
CRIT_DATA = load_json("critical_hits_master.json")
FUMBLE_DATA = load_json("fumbles_master.json")

# Initial data integrity checks
if not CRIT_DATA: 
    app.logger.warning("CRIT_DATA is empty or failed to load.")
if not FUMBLE_DATA: 
    app.logger.warning("FUMBLE_DATA is empty or failed to load.")


# --- Geolocation Helper (refactored to use security utilities) ---
def get_geolocation(ip_address):
    """Get geolocation using the secure IPRedactor utility."""
    return IPRedactor.get_geolocation(ip_address, app.logger)

# --- Helper Functions ---
def resolve_roll(roll_value, table):
    """Resolve a dice roll value against a table of results."""
    if not isinstance(table, dict): 
        app.logger.warning(f"Invalid table to resolve_roll: {type(table)}")
        return "Invalid table data."
    
    try:
        val = int(roll_value)
        for key, result_text in table.items():
            if '-' in key: 
                start, end = map(int, key.split('-'))
                matches = start <= val <= end
            else: 
                matches = str(val) == key
            
            if matches: 
                return result_text
                
    except (ValueError, TypeError) as e: 
        app.logger.error(f"Error resolving roll {roll_value}: {e}", exc_info=True)
    
    table_preview = str(table)[:200] + '...' if len(str(table)) > 200 else str(table)
    app.logger.warning(f"No result for roll {roll_value} in table {table_preview}")
    return "No result found for this roll in the table."


# --- Main Roll Logic & Narrative Logging ---
def get_roll_result_and_log(payload, client_ip=None):
    geo_info = get_geolocation(client_ip)
    response = {"status": "success", "rollValue": None, "resultText": None, "description": None, "effect": None, 
                  "isSecondaryPrompt": False, "secondaryPromptText": None, "secondaryType": None, 
                  "primaryRollValueForSecondary": payload.get('primaryRollValue'), 
                  "primaryResultForSecondary": payload.get('primaryResultText'), "errorMessage": None,
                  "selectedRollType": payload.get('rollType'), "selectedCritSource": payload.get('critSource'), 
                  "selectedFumbleType": payload.get('fumbleType'), "selectedAttackType": payload.get('attackType'), 
                  "numDice": 1, "dieType": "d20",
                  "original_damageType": payload.get('damageType'),    # Pass original damageType from request
                  "original_magicSubtype": payload.get('magicSubtype') # Pass original magicSubtype from request
    }

    roll_context = payload.get('rollContext', 'primary')
    roll_type_from_payload = payload.get('rollType')
    damage_type = payload.get('damageType')
    magic_subtype = payload.get('magicSubtype')
    fumble_source_from_payload = payload.get('fumbleType')
    attack_type = payload.get('attackType')

    try:
        if roll_context == 'primary':
            if roll_type_from_payload == 'crit':
                crit_source_from_payload = payload.get('critSource', 'Sterling Vermin')
                response["selectedCritSource"] = crit_source_from_payload

                if crit_source_from_payload in ["Questionable Arcana", "BCoydog", "Fury & Folly"]:
                    response["dieType"], response["numDice"], roll_value = "d100", 1, random.randint(1, 100)
                else: # Sterling Vermin
                    response["dieType"], response["numDice"], roll_value = "d20", 1, random.randint(1, 20)
                response["rollValue"] = roll_value
                
                crit_damage_key = (damage_type.lower().strip() if damage_type else 'slashing')
                
                source_tables = CRIT_DATA.get(crit_source_from_payload, {})
                if not source_tables: response.update({"status": "error", "errorMessage": f"Invalid Crit source: {crit_source_from_payload}"})
                else:
                    table_data = source_tables.get(crit_damage_key)
                    if table_data:
                        res_text = resolve_roll(roll_value, table_data)
                        text_for_injury_check = res_text 

                        if crit_source_from_payload == "Questionable Arcana" and isinstance(res_text, str):
                            parts = res_text.split(" Effect: ", 1)
                            if len(parts) == 2: response["description"], response["effect"], response["resultText"] = parts[0].strip(), parts[1].strip(), None
                            else: response["description"], response["effect"], response["resultText"] = res_text, "Details not separated.", None
                        elif crit_source_from_payload in ["BCoydog", "Fury & Folly"] and isinstance(res_text, str):
                            parts = res_text.split(": ", 1)
                            if len(parts) == 2: response["description"], response["effect"], response["resultText"] = parts[0].strip(), parts[1].strip(), None
                            else: response["description"], response["effect"], response["resultText"] = res_text, "Details not separated.", None
                        else: response["resultText"] = res_text

                        if isinstance(text_for_injury_check, str):
                            if "minor injury" in text_for_injury_check.lower(): response.update({"isSecondaryPrompt": True, "secondaryPromptText": "Minor Injury!", "secondaryType": "minor"})
                            elif "major injury" in text_for_injury_check.lower(): response.update({"isSecondaryPrompt": True, "secondaryPromptText": "Major Injury!", "secondaryType": "major"})
                            elif "insanity" in text_for_injury_check.lower(): response.update({"isSecondaryPrompt": True, "secondaryPromptText": "Insanity!", "secondaryType": "insanity"})
                    else: response.update({"status": "error", "errorMessage": f"Invalid damage type '{crit_damage_key}' for {crit_source_from_payload} Crits."})

            elif roll_type_from_payload == 'fumble':
                response["dieType"], response["numDice"], roll_value = "d100", 1, random.randint(1, 100)
                response["rollValue"] = roll_value
                response["selectedFumbleType"] = fumble_source_from_payload
                
                fumble_src_tables = FUMBLE_DATA.get(fumble_source_from_payload, {})
                if not fumble_src_tables: 
                    response.update({"status": "error", "errorMessage": f"Invalid fumble source: {fumble_source_from_payload}"})
                else:
                    # START BUG FIX MODIFICATION for fumble key selection
                    key_to_use = None
                    if fumble_source_from_payload == 'Questionable Arcana':
                        # QA expects 'Weapon' or 'Magic' from frontend for attack_type
                        key_to_use = "Weapon Attack" if attack_type == 'Weapon' else "Spell Attack"
                    elif fumble_source_from_payload == 'BCoydog':
                        # BCoydog will receive 'melee', 'ranged', or 'magic' (lowercase) from frontend for attack_type
                        # These directly map to keys in fumbles_master.json for BCoydog
                        key_to_use = attack_type.lower() if attack_type else None
                        if key_to_use not in ['melee', 'ranged', 'magic']: # Basic validation
                            app.logger.warning(f"Received unexpected attack_type '{attack_type}' for BCoydog fumble. Defaulting to general or error.")
                            # key_to_use might become None or rely on fallback logic if attack_type is invalid
                            # For robustness, if it's invalid, perhaps force an error or a specific fallback.
                            # For now, if it's not one of these, f_list might be empty and trigger error below.
                            pass # Let the existing fallback or error handling catch invalid keys
                    elif fumble_source_from_payload == 'Fury & Folly':
                        key_to_use = attack_type.lower() if attack_type else None
                        if key_to_use not in ['physical', 'elemental', 'magical']:
                            key_to_use = None
                    else:
                        response.update({"status": "error", "errorMessage": f"Fumble logic not defined for source: {fumble_source_from_payload}"})
                    # END BUG FIX MODIFICATION for fumble key selection

                    if key_to_use:
                        f_list = fumble_src_tables.get(key_to_use, [])
                        
                        # Fallback logic for BCoydog if the specific key ('melee', 'ranged', 'magic') yields no list
                        # or if key_to_use was invalid and resulted in empty f_list for BCoydog
                        if not f_list and fumble_source_from_payload == 'BCoydog':
                            general_fumbles = fumble_src_tables.get('general', [])
                            if general_fumbles:
                                app.logger.info(f"Fumble key '{key_to_use}' for BCoydog resulted in empty list or was invalid. Falling back to 'general' fumbles.")
                                f_list = general_fumbles
                                key_to_use = 'general' # Update key_to_use for error message consistency
                            
                        if not f_list: 
                            response.update({"status": "error", "errorMessage": f"No fumble entries for {fumble_source_from_payload} - {key_to_use} (including fallback)." })
                        else:
                            found = False
                            for entry in f_list:
                                rr_str = entry.get('roll'); match = False
                                if not rr_str: continue
                                try:
                                    if '-' in rr_str: l, h = map(int, rr_str.split('-')); match = l <= roll_value <= h
                                    else: match = int(rr_str) == roll_value
                                except ValueError: app.logger.warning(f"Malformed roll '{rr_str}' in {fumble_source_from_payload}"); continue
                                if match: response.update({"description": entry.get('description', 'N/A'), "effect": entry.get('effect', 'N/A')}); found = True; break
                            if not found: response.update({"description": f"No matching {fumble_source_from_payload} fumble for {roll_value} in {key_to_use}.", "effect": "No additional effect."})
                    # If key_to_use was None (e.g. from undefined fumble source), error is already set.
            else: response.update({"status": "error", "errorMessage": f"Invalid primary roll type: {roll_type_from_payload}"})

        elif roll_context == 'secondary':
            response["dieType"], response["numDice"], roll_value = "d20", 1, random.randint(1, 20)
            response["rollValue"] = roll_value
            sec_map = {'minor': 'minor_injuries', 'major': 'major_injuries', 'insanity': 'insanities'}
            sec_key = sec_map.get(roll_type_from_payload)
            if sec_key:
                eff_data = CRIT_DATA.get('effects_tables', {}).get(sec_key, {})
                if eff_data: response["secondaryResultText"] = resolve_roll(roll_value, eff_data)
                else: response.update({"status": "error", "errorMessage": f"Secondary table '{sec_key}' not found."})
            else: response.update({"status": "error", "errorMessage": f"Invalid secondary roll type: {roll_type_from_payload}"})
        else: response.update({"status": "error", "errorMessage": f"Invalid roll context: {roll_context}"})
    except Exception as e:
        app.logger.error(f"Error processing roll: {e}", exc_info=True)
        response.update({"status": "error", "errorMessage": f"An internal error occurred: {str(e)}"})

    if response["status"] == "success":
        desc = random.choice(RANDOM_DESCRIPTORS); city = geo_info.get("city", "city?"); region = geo_info.get("regionName", "region?")
        rval = response.get("rollValue"); t_name = "Unknown Table"; res_log = "N/A"
        if roll_context == 'primary':
            if roll_type_from_payload == 'crit':
                src = response.get("selectedCritSource", "?"); dmg_key = (payload.get('damageType') or "?").lower()
                t_name = f"{src} Crit ({dmg_key.title()})"
                res_log = response.get("description") + " Effect: " + response.get("effect") if response.get("description") and response.get("effect") else response.get("resultText", "N/A")
            elif roll_type_from_payload == 'fumble':
                src = response.get("selectedFumbleType", "?"); atk = response.get("selectedAttackType", "?") # atk will be 'melee', 'ranged', 'magic' for BCoydog
                t_name = f"{src} Fumble ({atk.title() if atk else 'Unknown'})"; # .title() for display
                d, e = response.get("description", ""), response.get("effect", "")
                res_log = f"{d} Effect: {e}".strip() if e else d
        elif roll_context == 'secondary': t_name = f"{roll_type_from_payload.title()} Effect"; res_log = response.get("secondaryResultText", "N/A")
        
        d_words = desc.split(' '); art = d_words[0].capitalize() if d_words[0].lower() in ["a","an"] else ("An" if desc[0].lower() in 'aeiou' else "A")
        d_noun = ' '.join(d_words[1:]) if d_words[0].lower() in ["a","an"] else desc
        log_entry = f"{art} {d_noun} from {city}, {region} rolled {rval} on {t_name}, resulting in: \u201c{str(res_log).strip()}\u201d"
        if response.get("isSecondaryPrompt") and not response.get("secondaryResultText"): log_entry += " (Bonus roll pending...)"
        try:
            log_data = {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),"narrative": log_entry,"raw_payload": payload,"raw_response": response}
            with open(NARRATIVE_LOG_FILE_PATH, "a", encoding="utf-8") as lf: lf.write(json.dumps(log_data) + "\n")
            print(f"NARRATIVE LOG: {log_entry}")
        except Exception as e: app.logger.error(f"Log write error: {e}", exc_info=True); print(f"CRITICAL: Log write fail: {e}")
    return response

# --- Routes ---
@app.route('/', methods=['GET'])
def index():
    sv_tables = CRIT_DATA.get('Sterling Vermin', {})
    dmg_types = sorted([k for k in sv_tables.keys() if not k.startswith('magic:')])
    magic_subs = sorted([k for k in sv_tables.keys() if k.startswith('magic:')])
    return render_template('index.html', damage_types=dmg_types, magic_subtypes=magic_subs,
                           selected_damage_type="slashing", selected_roll_type="crit",
                           selected_crit_source="Fury & Folly", selected_fumble_type="Fury & Folly",
                           selected_attack_type="Physical")

@app.route('/roll', methods=['POST'])
def roll_ajax():
    # Extract client IP for rate limiting and geolocation
    xff = request.headers.get('X-Forwarded-For')
    client_ip = xff.split(',')[0].strip() if xff else request.remote_addr
    
    # Apply rate limiting: 20 rolls per minute per IP (skip in development)
    if not app.config.get('DISABLE_RATE_LIMITING', False):
        if not rate_limiter.is_allowed(client_ip, limit=20, window_minutes=1):
            app.logger.warning(f"Rate limit exceeded for {IPRedactor.REDACTED_PLACEHOLDER}")
            return jsonify(*error_handler.create_error_response(
                "Rate limit exceeded. Please wait before making more requests.", 
                429, 
                "rate_limit"
            ))
    
    # Validate request data
    p = request.get_json()
    app.logger.info(f"Roll request from {IPRedactor.REDACTED_PLACEHOLDER}: {p}")
    
    if not p: 
        return jsonify(*error_handler.create_error_response("Invalid request data.", 400, "validation"))
    
    # Process the roll request
    return jsonify(get_roll_result_and_log(p, client_ip))

@app.route('/share_discord', methods=['POST'])
def share_discord():
    # Extract client IP for rate limiting
    xff = request.headers.get('X-Forwarded-For')
    client_ip = xff.split(',')[0].strip() if xff else request.remote_addr
    
    # Apply rate limiting: 5 Discord shares per minute per IP (skip in development)
    if not app.config.get('DISABLE_RATE_LIMITING', False):
        if not rate_limiter.is_allowed(client_ip, limit=5, window_minutes=1):
            app.logger.warning(f"Discord share rate limit exceeded for {IPRedactor.REDACTED_PLACEHOLDER}")
            return jsonify(*error_handler.create_error_response(
                "Rate limit exceeded. Please wait before sharing again.", 
                429, 
                "rate_limit"
            ))
    
    # Validate request data
    payload = request.get_json()
    if not payload or not payload.get('message'):
        app.logger.warning(f"Invalid Discord share request from {IPRedactor.REDACTED_PLACEHOLDER}")
        return jsonify({"status": "error", "error": "No message content provided."}), 400
    
    # Check for webhook URL from request payload
    webhook_url = payload.get('webhookUrl')
    if not webhook_url: 
        app.logger.error("No Discord webhook URL provided")
        return jsonify({"status": "error", "error": "No Discord webhook URL provided."}), 400
    
    # Basic webhook URL validation
    if not webhook_url.startswith('https://discord.com/api/webhooks/') and not webhook_url.startswith('https://discordapp.com/api/webhooks/'):
        app.logger.warning(f"Invalid Discord webhook URL format from {IPRedactor.REDACTED_PLACEHOLDER}")
        return jsonify({"status": "error", "error": "Invalid Discord webhook URL format."}), 400
    
    message = payload.get('message')
    
    # Basic message validation and sanitization
    if len(message) > 2000:  # Discord's character limit
        app.logger.warning(f"Discord message too long from {IPRedactor.REDACTED_PLACEHOLDER}")
        return jsonify({"status": "error", "error": "Message too long for Discord."}), 400
    
    try:
        # Send to Discord
        response = requests.post(
            webhook_url, 
            json={'content': message}, 
            timeout=10  # Add timeout for external request
        )
        response.raise_for_status()
        
        app.logger.info(f"Successful Discord share from {IPRedactor.REDACTED_PLACEHOLDER}")
        return jsonify({"status": "success"})
        
    except requests.exceptions.Timeout:
        app.logger.error("Discord webhook request timed out")
        return jsonify({"status": "error", "error": "Discord service temporarily unavailable."}), 503
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Discord webhook error: {e}")
        return jsonify({"status": "error", "error": "Failed to send to Discord."}), 503
        
    except Exception as e:
        app.logger.error(f"Unexpected Discord share error: {e}", exc_info=True)
        return jsonify({"status": "error", "error": "An unexpected error occurred."}), 500
    
@app.route('/get_roll_history', methods=['GET'])
def get_roll_history():
    """Get recent roll history with proper error handling and logging."""
    # Extract client IP for rate limiting
    xff = request.headers.get('X-Forwarded-For')
    client_ip = xff.split(',')[0].strip() if xff else request.remote_addr
    
    # Apply rate limiting: 10 history requests per minute per IP (skip in development)
    if not app.config.get('DISABLE_RATE_LIMITING', False):
        if not rate_limiter.is_allowed(client_ip, limit=10, window_minutes=1):
            app.logger.warning(f"History rate limit exceeded for {IPRedactor.REDACTED_PLACEHOLDER}")
            return jsonify({"status": "error", "message": "Rate limit exceeded."}), 429
    
    if not os.path.exists(NARRATIVE_LOG_FILE_PATH):
        app.logger.debug("No history file found")
        return jsonify([])
    
    try:
        logs = []
        with open(NARRATIVE_LOG_FILE_PATH, "r", encoding="utf-8") as log_file:
            lines = log_file.readlines()
        
        # Process last 50 entries
        for line in lines[-50:]:
            line = line.strip()
            if not line:
                continue
                
            try:
                entry = json.loads(line)
                timestamp = entry.get("timestamp")
                narrative = entry.get("narrative")
                
                if timestamp and narrative:
                    logs.append({
                        "timestamp": timestamp, 
                        "narrative": narrative
                    })
            except json.JSONDecodeError as json_error:
                app.logger.warning(f"Invalid JSON in history line: {json_error}")
                continue
        
        # Return in reverse chronological order (newest first)
        result = list(reversed(logs))
        app.logger.debug(f"Retrieved {len(result)} history entries for {IPRedactor.REDACTED_PLACEHOLDER}")
        return jsonify(result)
        
    except FileNotFoundError:
        app.logger.warning("History file not found during read")
        return jsonify([])
        
    except PermissionError:
        app.logger.error("Permission denied reading history file")
        return jsonify({"status": "error", "message": "Unable to access history."}), 500
        
    except Exception as e:
        app.logger.error(f"Unexpected error reading history: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Error retrieving history."}), 500

if __name__ == '__main__':
    app.run()