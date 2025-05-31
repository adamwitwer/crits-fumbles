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
# User will set LOG_STORAGE_DIR to their disk mount point (e.g., /var/data) on Render.
# Defaults to current directory ('.') for local development if the env var is not set.
LOG_STORAGE_DIR = os.environ.get('LOG_STORAGE_DIR', '.')
LOG_FILENAME = "narrative_dice_log.jsonl"
NARRATIVE_LOG_FILE_PATH = os.path.join(LOG_STORAGE_DIR, LOG_FILENAME)

# --- Ensure the log directory exists ---
# This block runs once when the application starts.
try:
    os.makedirs(LOG_STORAGE_DIR, exist_ok=True)
    # Use app.logger for startup messages, as print might not be visible at this stage on some platforms.
    app.logger.info(f"Log directory ensured/created: {LOG_STORAGE_DIR}")
    app.logger.info(f"Application will use log file at: {NARRATIVE_LOG_FILE_PATH}")
except OSError as e:
    app.logger.error(f"CRITICAL: Error creating log directory {LOG_STORAGE_DIR}: {e}. Log persistence may fail.", exc_info=True)
    # Fallback to current directory if disk path creation fails.
    app.logger.warning(f"Falling back to using log file in current directory: '.' due to error with {LOG_STORAGE_DIR}.")
    # Update NARRATIVE_LOG_FILE_PATH to the fallback path
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

DATA = load_json("crits_and_fumbles_v2.json")
ARCANA = load_json("fumbles_arcana.json")
if not DATA.get('crit_tables') or not DATA.get('fumbles'):
    app.logger.warning("Warning: Core data from crits_and_fumbles_v2.json might be missing.")
if not ARCANA:
     app.logger.warning("Warning: Arcana data from fumbles_arcana.json might be missing.")

# --- Geolocation Helper (REVISED FUNCTION) ---
def get_geolocation(ip_address):
    """Fetches city and region for an IP address, with special handling for local/Tailscale IPs."""

    if not ip_address: # Should ideally not happen if client_ip is always derived
        return {"city": "an unknown void", "regionName": "the ether"}

    try:
        ip_obj = ipaddress.ip_address(ip_address)

        if ip_obj.is_loopback: # Covers 127.0.0.1 etc.
            return {"city": "their cozy terminal", "regionName": "the local machine"}
        if ip_obj.is_private: # Covers 192.168.x.x, 10.x.x.x, 172.16.x.x-172.31.x.x
            return {"city": "their local sanctum", "regionName": "the home network"}

        tailscale_cgnat_network = ipaddress.ip_network('100.64.0.0/10', strict=False)
        if ip_obj in tailscale_cgnat_network:
            return {"city": "their secure Tailnet", "regionName": "a private dimension"}

    except ValueError:
        app.logger.warning(f"Invalid IP address format for geolocation: {ip_address}")
        if isinstance(ip_address, str) and ip_address.lower() == "localhost":
             return {"city": "their cozy terminal", "regionName": "the local machine"}
        return {"city": "an unidentifiable nexus", "regionName": "a glitch in the matrix"}

    try:
        url = f"http://ip-api.com/json/{ip_address}?fields=status,message,city,regionName,query"
        response = requests.get(url, timeout=3)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            return {
                "city": data.get("city", "an unknown city"),
                "regionName": data.get("regionName", "an uncharted territory")
            }
        else:
            app.logger.warning(f"Geolocation API error for IP {ip_address}: {data.get('message', 'Unknown error from ip-api.com')}")
            return {"city": "parts unknown", "regionName": "a mysterious land"}
    except requests.exceptions.Timeout:
        app.logger.warning(f"Geolocation request timed out for IP {ip_address}")
        return {"city": "a realm beyond reach", "regionName": "the mists of time"}
    except requests.exceptions.RequestException as e:
        app.logger.warning(f"Error fetching geolocation for IP {ip_address}: {e}")
        return {"city": "a digital realm", "regionName": "the boundless interwebs"}
    except json.JSONDecodeError:
        app.logger.warning(f"Failed to decode JSON from geolocation API for IP {ip_address}")
        return {"city": "a garbled signal", "regionName": "the static void"}
    except Exception as e:
        app.logger.error(f"Generic error in get_geolocation for IP {ip_address} during API call: {e}", exc_info=True)
        return {"city": "a place beyond perception", "regionName": "the void"}


# --- Helper Functions (resolve_roll remains the same) ---
def resolve_roll(roll_value, table):
    if not isinstance(table, dict):
        app.logger.warning(f"Warning: Invalid table provided to resolve_roll: {type(table)}")
        return "Invalid table data."
    try:
        val = int(roll_value)
        for key, result_text in table.items():
            if '-' in key:
                start, end = map(int, key.split('-'))
                if start <= val <= end:
                    return result_text
            elif str(val) == key:
                return result_text
    except (ValueError, TypeError) as e:
        app.logger.error(f"Error resolving roll {roll_value}: {e}", exc_info=True)
        pass
    return "No result found."

# --- Main Roll Logic & Narrative Logging ---
def get_roll_result_and_log(payload, client_ip=None):
    """Processes roll request, generates result, and logs a narrative entry."""
    geo_info = get_geolocation(client_ip)

    response = {
        "status": "success", "rollValue": None, "resultText": None, "description": None,
        "effect": None, "isSecondaryPrompt": False, "secondaryPromptText": None,
        "secondaryType": None, "primaryRollValueForSecondary": payload.get('primaryRollValue', None),
        "primaryResultForSecondary": payload.get('primaryResultText', None), "errorMessage": None,
        "selectedRollType": payload.get('rollType'),
        "selectedFumbleType": payload.get('fumbleType'),
        "selectedAttackType": payload.get('attackType'),
        "numDice": 1, "dieType": "d20"
    }

    roll_context = payload.get('rollContext', 'primary')
    roll_type_from_payload = payload.get('rollType')
    damage_type = payload.get('damageType')
    magic_subtype = payload.get('magicSubtype')
    fumble_type_from_payload = payload.get('fumbleType')
    attack_type = payload.get('attackType')

    try:
        if roll_context == 'primary':
            if roll_type_from_payload == 'crit':
                response["dieType"] = "d20"; response["numDice"] = 1
                roll_value = random.randint(1, 20); response["rollValue"] = roll_value
                crit_damage_type = magic_subtype if damage_type == 'magic' else damage_type
                crit_damage_type = crit_damage_type.lower().strip() if crit_damage_type else 'slashing'
                table_data = DATA.get('crit_tables', {}).get(crit_damage_type)
                if table_data:
                    result_text = resolve_roll(roll_value, table_data)
                    response["resultText"] = result_text
                    if isinstance(result_text, str):
                        if "minor injury" in result_text.lower():
                            response.update({"isSecondaryPrompt": True, "secondaryPromptText": "Minor Injury!", "secondaryType": "minor"})
                        elif "major injury" in result_text.lower():
                            response.update({"isSecondaryPrompt": True, "secondaryPromptText": "Major Injury!", "secondaryType": "major"})
                        elif "insanity" in result_text.lower():
                            response.update({"isSecondaryPrompt": True, "secondaryPromptText": "Insanity!", "secondaryType": "insanity"})
                else:
                    response.update({"status": "error", "errorMessage": f"Invalid damage type for Crit: {crit_damage_type}"})

            elif roll_type_from_payload == 'fumble':
                response["dieType"] = "d10"; response["numDice"] = 2
                roll_value = random.randint(1, 100); response["rollValue"] = roll_value
                if fumble_type_from_payload == 'Questionable Arcana':
                    attack_type_map = {"Weapon": "Weapon Attack", "Magic": "Spell Attack"}
                    attack_key = attack_type_map.get(attack_type, "Weapon Attack")
                    fumble_list = ARCANA.get(attack_key, [])
                    found_arcana = False
                    for entry in fumble_list:
                        roll_entry_str = entry.get('roll')
                        if not roll_entry_str: continue
                        if '-' in roll_entry_str:
                            low, high = map(int, roll_entry_str.split('-'))
                            match = low <= roll_value <= high
                        else:
                            match = int(roll_entry_str) == roll_value
                        if match:
                            response.update({"description": entry.get('description', 'N/A'), "effect": entry.get('effect', 'N/A')}); found_arcana = True; break
                    if not found_arcana: response.update({"description": "No matching Arcana fumble found.", "effect": "No additional effect."})
                else: # Smack Down Fumble
                    fumble_table = DATA.get('fumbles', {})
                    response["resultText"] = resolve_roll(roll_value, fumble_table)
            else:
                response.update({"status": "error", "errorMessage": f"Invalid primary roll type: {roll_type_from_payload}"})

        elif roll_context == 'secondary':
            response["dieType"] = "d20"; response["numDice"] = 1
            roll_value = random.randint(1, 20); response["rollValue"] = roll_value
            secondary_table_key_map = {'minor': 'minor_injuries', 'major': 'major_injuries', 'insanity': 'insanities'}
            secondary_table_key = secondary_table_key_map.get(roll_type_from_payload)
            if secondary_table_key:
                secondary_table_data = DATA.get(secondary_table_key, {})
                response["secondaryResultText"] = resolve_roll(roll_value, secondary_table_data)
            else:
                response.update({"status": "error", "errorMessage": f"Invalid secondary roll type: {roll_type_from_payload}"})
        else:
            response.update({"status": "error", "errorMessage": f"Invalid roll context: {roll_context}"})

    except Exception as e:
        app.logger.error(f"Error processing roll: {e}", exc_info=True)
        response.update({"status": "error", "errorMessage": f"An internal error occurred processing the roll: {str(e)}"})

    if response["status"] == "success":
        descriptor = random.choice(RANDOM_DESCRIPTORS)
        city = geo_info.get("city", "an undisclosed city")
        region = geo_info.get("regionName", "an unknown region")
        rolled_value = response.get("rollValue")
        
        table_name_for_log = "Unknown Table"
        result_for_log = ""

        if roll_context == 'primary':
            if roll_type_from_payload == 'crit':
                effective_damage_type = magic_subtype if damage_type == 'magic' else damage_type
                crit_damage_type_for_log = effective_damage_type.lower().strip() if effective_damage_type else 'slashing'
                table_name_for_log = f"Critical Hit ({crit_damage_type_for_log.title()})"
                result_for_log = response.get("resultText", "No specific result text.")
            elif roll_type_from_payload == 'fumble':
                if fumble_type_from_payload == 'Questionable Arcana':
                    table_name_for_log = f"Questionable Arcana Fumble ({attack_type})"
                    desc = response.get("description", "")
                    eff = response.get("effect", "")
                    result_for_log = f"{desc} Effect: {eff}".strip()
                else: # Smack Down Fumble
                    table_name_for_log = "Smack Down Fumble"
                    result_for_log = response.get("resultText", "No specific result text.")
        elif roll_context == 'secondary':
            table_name_for_log = f"{roll_type_from_payload.title()} Effect"
            result_for_log = response.get("secondaryResultText", "No specific secondary result.")
        
        result_for_log_str = str(result_for_log).strip()
        
        descriptor_words = descriptor.split(' ')
        if descriptor_words[0].lower() in ["a", "an"]:
            article_for_narrative = descriptor_words[0].capitalize()
            descriptor_noun_phrase = ' '.join(descriptor_words[1:])
        else:
            descriptor_noun_phrase = descriptor
            if descriptor_noun_phrase and descriptor_noun_phrase[0].lower() in 'aeiou':
                article_for_narrative = "An"
            else:
                article_for_narrative = "A"
        
        narrative_log_entry = f"{article_for_narrative} {descriptor_noun_phrase} from {city}, {region} rolled a {rolled_value} on the {table_name_for_log} table, resulting in: \u201c{result_for_log_str}\u201d"
        
        if response.get("isSecondaryPrompt") and not response.get("secondaryResultText"):
            narrative_log_entry += " (Bonus roll pending...)"

        try:
            log_data_to_store = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "narrative": narrative_log_entry,
                "geo_debug": {"ip": client_ip, "city_resolved": city, "region_resolved": region},
                "raw_payload": payload,
                "raw_response": response # Be mindful of what's in response; it could be large or sensitive
            }
            # Use NARRATIVE_LOG_FILE_PATH defined globally
            with open(NARRATIVE_LOG_FILE_PATH, "a", encoding="utf-8") as logfile:
                logfile.write(json.dumps(log_data_to_store) + "\n")
            # This print will go to Render's standard log stream
            print(f"NARRATIVE LOG: {narrative_log_entry}")
        except Exception as e:
            app.logger.error(f"Error writing narrative log to {NARRATIVE_LOG_FILE_PATH}: {e}", exc_info=True)
            # Also print to Render's console for immediate visibility if logger isn't fully configured for stdout
            print(f"CRITICAL: Failed to write to log file {NARRATIVE_LOG_FILE_PATH}. Error: {e}")


    return response

# --- Routes ---
@app.route('/', methods=['GET'])
def index():
    initial_damage_type = "slashing"
    crit_tables = DATA.get('crit_tables', {})
    damage_types_list = sorted(crit_tables.keys()) if crit_tables else []
    return render_template('index.html',
                          damage_types=damage_types_list,
                          selected_damage_type=initial_damage_type,
                          selected_roll_type="crit",
                          selected_fumble_type="Smack Down",
                          selected_attack_type="Weapon"
                          )

@app.route('/roll', methods=['POST'])
def roll_ajax():
    payload = request.get_json()
    if not payload:
        return jsonify({"status": "error", "errorMessage": "Invalid request data."}), 400

    xff = request.headers.get('X-Forwarded-For')
    if xff:
        client_ip = xff.split(',')[0].strip()
    else:
        client_ip = request.remote_addr

    app.logger.info(f"Attempting geolocation for IP address: {client_ip} (XFF: {request.headers.get('X-Forwarded-For')}, Remote: {request.remote_addr})")
    
    result_data = get_roll_result_and_log(payload, client_ip=client_ip)
    return jsonify(result_data)

@app.route('/share_discord', methods=['POST'])
def share_discord():
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        app.logger.error("Error: DISCORD_WEBHOOK_URL not set.")
        return jsonify({"status": "error", "error": "Discord webhook URL not configured on server."}), 500
    payload = request.get_json()
    message_content = payload.get('message')
    if not message_content:
        return jsonify({"status": "error", "error": "No message content provided."}), 400
    discord_data = {'content': message_content}
    try:
        response_discord = requests.post(webhook_url, json=discord_data)
        response_discord.raise_for_status()
        app.logger.info("Message sent to Discord successfully!")
        return jsonify({"status": "success"})
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error sending message to Discord: {e}", exc_info=True)
        return jsonify({"status": "error", "error": f"Failed to send request to Discord: {str(e)}"}), 500
    
# --- Roll History Endpoint (using logs) ---
@app.route('/get_roll_history', methods=['GET'])
def get_roll_history():
    try:
        logs = []
        max_logs_to_return = 50

        # Use NARRATIVE_LOG_FILE_PATH defined globally
        if not os.path.exists(NARRATIVE_LOG_FILE_PATH):
            app.logger.info(f"Log file not found at {NARRATIVE_LOG_FILE_PATH} for history retrieval.")
            return jsonify([])

        # Use NARRATIVE_LOG_FILE_PATH defined globally
        with open(NARRATIVE_LOG_FILE_PATH, "r", encoding="utf-8") as logfile:
            all_lines = logfile.readlines()
        
        recent_lines = all_lines[-max_logs_to_return:]

        for line in recent_lines:
            try:
                log_entry = json.loads(line)
                logs.append({
                    "timestamp": log_entry.get("timestamp"),
                    "narrative": log_entry.get("narrative")
                })
            except json.JSONDecodeError:
                app.logger.warning(f"Skipping malformed log line during history retrieval: {line.strip()}")

        return jsonify(list(reversed(logs))) 
    except Exception as e:
        app.logger.error(f"Error reading roll history from {NARRATIVE_LOG_FILE_PATH}: {e}", exc_info=True)
        return jsonify({"status": "error", "errorMessage": "Could not retrieve roll history."}), 500

if __name__ == '__main__':
    # For production, Gunicorn or another WSGI server is recommended.
    # The app.run() is fine for local development.
    # Flask's default logger is used. For more advanced logging configurations,
    # you might set up handlers, formatters, and levels, especially for production.
    # Example (can be expanded):
    # import logging
    # if not app.debug:
    #     # Example: Log to stdout which Render captures
    #     stream_handler = logging.StreamHandler()
    #     stream_handler.setLevel(logging.INFO)
    #     app.logger.addHandler(stream_handler)
    #     app.logger.setLevel(logging.INFO)
    # else:
    #     app.logger.setLevel(logging.DEBUG)

    app.run()