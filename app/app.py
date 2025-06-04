from dotenv import load_dotenv
load_dotenv()

import requests
import os
import json
import random
from flask import Flask, render_template, request, jsonify, url_for
import datetime # For timestamps in logs
import ipaddress

app = Flask(__name__)

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

# Initial data integrity checks (simplified for brevity in this example)
if not CRIT_DATA: app.logger.warning("CRIT_DATA is empty or failed to load.")
if not FUMBLE_DATA: app.logger.warning("FUMBLE_DATA is empty or failed to load.")


# --- Geolocation Helper ---
def get_geolocation(ip_address):
    # Use a placeholder for IP addresses in log messages to avoid logging the actual IP.
    ip_display_for_logs = "[IP REDACTED]"

    if not ip_address: return {"city": "an unknown void", "regionName": "the ether"}
    try:
        ip_obj = ipaddress.ip_address(ip_address)
        if ip_obj.is_loopback: return {"city": "their cozy terminal", "regionName": "the local machine"}
        if ip_obj.is_private: return {"city": "their local sanctum", "regionName": "the home network"}
        if ip_obj in ipaddress.ip_network('100.64.0.0/10', strict=False): return {"city": "their secure Tailnet", "regionName": "a private dimension"}
    except ValueError:
        # Handle cases like "localhost" string which is not a valid IP for ipaddress module
        if isinstance(ip_address, str) and ip_address.lower() == "localhost":
            return {"city": "their cozy terminal", "regionName": "the local machine"}
        # Log with the placeholder instead of the actual potentially invalid IP string
        app.logger.warning(f"Invalid IP format for geolocation: {ip_display_for_logs}")
        return {"city": "an unidentifiable nexus", "regionName": "a glitch in the matrix"}
    
    # For external API calls, the actual ip_address is still used.
    try:
        url = f"http://ip-api.com/json/{ip_address}?fields=status,message,city,regionName,query"
        response_geo = requests.get(url, timeout=3)
        response_geo.raise_for_status()
        data = response_geo.json()
        
        api_message = data.get('message', 'Unknown ip-api.com error')
        # Sanitize api_message if it might contain the IP (ip-api.com puts the IP in the 'query' field of its response)
        # and sometimes in the 'message' field for errors.
        if data.get("query") and isinstance(api_message, str) and data.get("query") in api_message:
            api_message = api_message.replace(data.get("query"), ip_display_for_logs)

        if data.get("status") == "success":
            return {"city": data.get("city", "unknown city"), "regionName": data.get("regionName", "uncharted territory")}
        
        app.logger.warning(f"Geo API error for {ip_display_for_logs}: {api_message}")
        return {"city": "parts unknown", "regionName": "mysterious land"}

    except requests.exceptions.Timeout:
        app.logger.warning(f"Geo request timed out for {ip_display_for_logs}")
        return {"city": "realm beyond reach", "regionName": "mists of time"}
    except requests.exceptions.RequestException as e:
        # Sanitize exception string if it's likely to contain the URL with the IP
        error_message = str(e)
        if isinstance(ip_address, str) and ip_address in error_message: # Check if the original IP is in the error string
            error_message = error_message.replace(ip_address, ip_display_for_logs)
        app.logger.warning(f"Error fetching geo for {ip_display_for_logs}: {error_message}")
        return {"city": "digital realm", "regionName": "boundless interwebs"}
    except json.JSONDecodeError:
        app.logger.warning(f"Failed to decode geo JSON for {ip_display_for_logs}")
        return {"city": "garbled signal", "regionName": "static void"}
    except Exception as e:
        # Sanitize generic exception messages as well
        error_message_generic = str(e)
        if isinstance(ip_address, str) and ip_address in error_message_generic:
             error_message_generic = error_message_generic.replace(ip_address, ip_display_for_logs)
        # exc_info=True will log the stack trace. Standard tracebacks don't show all local variables by default,
        # but the exception message itself (str(e)) is sanitized above.
        app.logger.error(f"Generic geo error for {ip_display_for_logs}: {error_message_generic}", exc_info=True)
        return {"city": "place beyond perception", "regionName": "the void"}

# --- Helper Functions ---
def resolve_roll(roll_value, table):
    if not isinstance(table, dict): app.logger.warning(f"Invalid table to resolve_roll: {type(table)}"); return "Invalid table data."
    try:
        val = int(roll_value)
        for key, result_text in table.items():
            if '-' in key: start, end = map(int, key.split('-')); شرط = start <= val <= end
            else: شرط = str(val) == key
            if شرط: return result_text
    except (ValueError, TypeError) as e: app.logger.error(f"Error resolving roll {roll_value}: {e}", exc_info=True)
    app.logger.warning(f"No result for roll {roll_value} in table {str(table)[:200] + '...' if len(str(table)) > 200 else table}")
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

                if crit_source_from_payload in ["Questionable Arcana", "BCoydog"]:
                    response["dieType"], response["numDice"], roll_value = "d100", 1, random.randint(1, 100)
                else: # Sterling Vermin
                    response["dieType"], response["numDice"], roll_value = "d20", 1, random.randint(1, 20)
                response["rollValue"] = roll_value
                
                crit_damage_key = (damage_type.lower().strip() if damage_type else None)
                if crit_source_from_payload == 'Sterling Vermin':
                    crit_damage_key = magic_subtype if damage_type == 'magic' else damage_type
                    crit_damage_key = (crit_damage_key.lower().strip() if crit_damage_key else 'slashing')
                
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
                        elif crit_source_from_payload == "BCoydog" and isinstance(res_text, str):
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
                if src == 'Sterling Vermin':
                    sv_sub = payload.get('magicSubtype'); sv_dmg = payload.get('damageType')
                    dmg_key = (sv_sub if sv_dmg == 'magic' else sv_dmg or 'slashing').lower()
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
                           selected_crit_source="Sterling Vermin", selected_fumble_type="Questionable Arcana", 
                           selected_attack_type="Weapon")

@app.route('/roll', methods=['POST'])
def roll_ajax():
    p = request.get_json(); print(f"Roll payload: {p}") 
    if not p: return jsonify({"status": "error", "errorMessage": "Invalid request data."}), 400
    xff = request.headers.get('X-Forwarded-For'); ip = xff.split(',')[0].strip() if xff else request.remote_addr
    return jsonify(get_roll_result_and_log(p, ip))

@app.route('/share_discord', methods=['POST'])
def share_discord(): 
    url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not url: return jsonify({"status": "error", "error": "Webhook URL not configured."}), 500
    p = request.get_json(); msg = p.get('message')
    if not msg: return jsonify({"status": "error", "error": "No message content."}), 400
    try: requests.post(url, json={'content': msg}).raise_for_status(); return jsonify({"status": "success"})
    except Exception as e: app.logger.error(f"Discord send error: {e}"); return jsonify({"status": "error", "error": str(e)}), 500
    
@app.route('/get_roll_history', methods=['GET'])
def get_roll_history(): 
    logs = []
    if not os.path.exists(NARRATIVE_LOG_FILE_PATH): return jsonify([])
    try:
        with open(NARRATIVE_LOG_FILE_PATH, "r", encoding="utf-8") as lf: lines = lf.readlines()
        for line in lines[-50:]:
            try: entry = json.loads(line); logs.append({"ts": entry.get("timestamp"), "nar": entry.get("narrative")})
            except: pass 
        return jsonify(list(reversed([{"timestamp":l["ts"], "narrative":l["nar"]} for l in logs if l.get("nar")])))
    except Exception as e: app.logger.error(f"History read error: {e}"); return jsonify({"status":"error","msg":"History fail."}),500

if __name__ == '__main__':
    app.run()