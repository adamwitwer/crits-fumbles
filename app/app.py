from dotenv import load_dotenv
load_dotenv()

import requests
import os
import json
import random
from collections import deque
from flask import Flask, render_template, request, jsonify, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
import datetime
import sys
sys.path.append(os.path.dirname(__file__))
from security_utils import IPRedactor, rate_limiter, csrf_protection, error_handler

app = Flask(__name__)

# --- Trust only the proxies actually in front of us ---
# Render's proxy appends to X-Forwarded-For without stripping what the client
# sent, so the leftmost entry is attacker-controlled and must never be trusted.
# Only the rightmost entries — added by infrastructure we control — are reliable,
# and ProxyFix resolves remote_addr from that trusted tail.
#
# The number of appending hops is not documented consistently by Render, so it is
# configurable: raise TRUSTED_PROXY_HOPS if every visitor resolves to the same
# address, and set it to 0 when serving with no proxy at all.
try:
    TRUSTED_PROXY_HOPS = int(os.environ.get('TRUSTED_PROXY_HOPS', '1'))
except ValueError:
    app.logger.warning("TRUSTED_PROXY_HOPS is not an integer; defaulting to 1.")
    TRUSTED_PROXY_HOPS = 1

if TRUSTED_PROXY_HOPS > 0:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=TRUSTED_PROXY_HOPS)

# Cloudflare fronts Render and overwrites CF-Connecting-IP on every request, so
# when present it is the client IP regardless of how long the XFF chain is.
TRUST_CF_CONNECTING_IP = os.environ.get('TRUST_CF_CONNECTING_IP', '1') != '0'

_logged_proxy_shape = False


def get_client_ip():
    """Client identity used for rate limiting and geolocation.

    Never reads the leftmost X-Forwarded-For entry: that is whatever the client
    chose to send. Prefers Cloudflare's spoof-resistant header, otherwise falls
    back to remote_addr as resolved by ProxyFix above. Keeping this in one place
    means the trust decision is made once rather than in each route.
    """
    global _logged_proxy_shape
    if not _logged_proxy_shape:
        # One line, once per worker, to make the deployed proxy shape verifiable
        # without logging any address: it says how to set TRUSTED_PROXY_HOPS.
        xff = request.headers.get('X-Forwarded-For', '')
        app.logger.info(
            f"Proxy shape: {len([p for p in xff.split(',') if p.strip()])} X-Forwarded-For entries, "
            f"CF-Connecting-IP {'present' if request.headers.get('CF-Connecting-IP') else 'absent'}, "
            f"TRUSTED_PROXY_HOPS={TRUSTED_PROXY_HOPS}"
        )
        _logged_proxy_shape = True

    if TRUST_CF_CONNECTING_IP:
        cf_ip = request.headers.get('CF-Connecting-IP')
        if cf_ip:
            return cf_ip.strip()

    return request.remote_addr

@app.after_request
def add_security_headers(response):
    csp_policy = (
        "default-src 'none';"
        "script-src 'self' 'sha256-xkCWla5qon65vOIHCOs7ZCr8zHIHr0UgJN5eX5r7PXU=';"
        "style-src 'self' 'unsafe-inline';"
        "img-src 'self' data:;"
        "media-src 'self';"
        "font-src 'self';"
        "connect-src 'self';"
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

# --- Accepted attack types per fumble source, mapped to their table key ---
# Lookup is case-insensitive; anything not listed here is rejected rather than
# being echoed back into the response and the Chronicles.
FUMBLE_ATTACK_KEYS = {
    'Questionable Arcana': {'weapon': 'Weapon Attack', 'magic': 'Spell Attack'},
    'BCoydog': {'melee': 'melee', 'ranged': 'ranged', 'magic': 'magic'},
    'Fury & Folly': {'physical': 'physical', 'elemental': 'elemental', 'magical': 'magical'},
}

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
                  "original_damageType": payload.get('damageType')    # Pass original damageType from request
    }

    roll_context = payload.get('rollContext', 'primary')
    roll_type_from_payload = payload.get('rollType')
    damage_type = payload.get('damageType')
    fumble_source_from_payload = payload.get('fumbleType')
    attack_type = payload.get('attackType')

    try:
        if roll_context == 'primary':
            if roll_type_from_payload == 'crit':
                crit_source_from_payload = payload.get('critSource', 'Sterling Vermin')
                response["selectedCritSource"] = crit_source_from_payload
                response["selectedAttackType"] = None  # not meaningful for crits; never echo the raw value back

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
                    # Resolve the attack type against the source's whitelist. Only a value
                    # that maps to a real table key is accepted back into the response.
                    attack_key_map = FUMBLE_ATTACK_KEYS.get(fumble_source_from_payload)
                    key_to_use = None
                    if attack_key_map is None:
                        response.update({"status": "error", "errorMessage": f"Fumble logic not defined for source: {fumble_source_from_payload}"})
                    elif isinstance(attack_type, str):
                        normalized_attack = attack_type.strip().lower()
                        key_to_use = attack_key_map.get(normalized_attack)
                        if key_to_use:
                            response["selectedAttackType"] = normalized_attack

                    # No usable table key (missing/unrecognized attack type) must surface as an
                    # error, otherwise the roll reports success with an empty result.
                    if not key_to_use and response["status"] != "error":
                        app.logger.warning(f"Rejected attack_type {attack_type!r} for {fumble_source_from_payload} fumble.")
                        response.update({"status": "error", "errorMessage": f"Invalid attack type for {fumble_source_from_payload} fumbles."})

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

                            # Detect references to follow-up injury/insanity tables in the fumble effect.
                            fumble_effect_text = response.get("effect", "")
                            if isinstance(fumble_effect_text, str):
                                if "minor injury" in fumble_effect_text.lower(): response.update({"isSecondaryPrompt": True, "secondaryPromptText": "Minor Injury!", "secondaryType": "minor"})
                                elif "major injury" in fumble_effect_text.lower(): response.update({"isSecondaryPrompt": True, "secondaryPromptText": "Major Injury!", "secondaryType": "major"})
                                elif "insanity" in fumble_effect_text.lower(): response.update({"isSecondaryPrompt": True, "secondaryPromptText": "Insanity!", "secondaryType": "insanity"})
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
    return render_template('index.html',
                           selected_damage_type="slashing", selected_roll_type="crit",
                           selected_crit_source="Fury & Folly", selected_fumble_type="Fury & Folly",
                           selected_attack_type="Physical")

@app.route('/roll', methods=['POST'])
def roll_ajax():
    client_ip = get_client_ip()

    # Apply rate limiting: 20 rolls per minute per IP (skip in development)
    if not app.config.get('DISABLE_RATE_LIMITING', False):
        if not rate_limiter.is_allowed(client_ip, limit=20, window_minutes=1):
            app.logger.warning(f"Rate limit exceeded for {IPRedactor.REDACTED_PLACEHOLDER}")
            body, code = error_handler.create_error_response(
                "Rate limit exceeded. Please wait before making more requests.",
                429,
                "rate_limit"
            )
            return jsonify(body), code
    
    # Validate request data
    p = request.get_json()
    app.logger.info(f"Roll request from {IPRedactor.REDACTED_PLACEHOLDER}: {p}")
    
    if not p:
        body, code = error_handler.create_error_response("Invalid request data.", 400, "validation")
        return jsonify(body), code
    
    # Process the roll request
    return jsonify(get_roll_result_and_log(p, client_ip))

@app.route('/share_discord', methods=['POST'])
def share_discord():
    client_ip = get_client_ip()

    # Apply rate limiting: 5 Discord shares per minute per IP (skip in development)
    if not app.config.get('DISABLE_RATE_LIMITING', False):
        if not rate_limiter.is_allowed(client_ip, limit=5, window_minutes=1):
            app.logger.warning(f"Discord share rate limit exceeded for {IPRedactor.REDACTED_PLACEHOLDER}")
            body, code = error_handler.create_error_response(
                "Rate limit exceeded. Please wait before sharing again.",
                429,
                "rate_limit"
            )
            return jsonify(body), code
    
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
            timeout=10,
            allow_redirects=False
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
    client_ip = get_client_ip()

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
            lines = deque(log_file, maxlen=50)

        for line in lines:
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