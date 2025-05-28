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
        print(f"Error: JSON file not found at {json_path}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_path}")
        return {}

DATA = load_json("crits_and_fumbles_v2.json")
ARCANA = load_json("fumbles_arcana.json")
if not DATA.get('crit_tables') or not DATA.get('fumbles'):
    print("Warning: Core data from crits_and_fumbles_v2.json might be missing.")
if not ARCANA:
     print("Warning: Arcana data from fumbles_arcana.json might be missing.")

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

        # Check for Tailscale's common CGNAT range (100.64.0.0/10)
        # strict=False is important as ip_obj is a single address
        tailscale_cgnat_network = ipaddress.ip_network('100.64.0.0/10', strict=False)
        if ip_obj in tailscale_cgnat_network:
            return {"city": "their secure Tailnet", "regionName": "a private dimension"}

    except ValueError:
        # If ip_address is not a valid IP string (e.g., "localhost" as a string, or malformed)
        print(f"Invalid IP address format for geolocation: {ip_address}")
        if isinstance(ip_address, str) and ip_address.lower() == "localhost":
             return {"city": "their cozy terminal", "regionName": "the local machine"}
        return {"city": "an unidentifiable nexus", "regionName": "a glitch in the matrix"}

    # If none of the above special IP types, proceed to query ip-api.com
    try:
        # Using specific fields to minimize data transfer and processing
        url = f"http://ip-api.com/json/{ip_address}?fields=status,message,city,regionName,query"
        # Increased timeout slightly just in case of slow network
        response = requests.get(url, timeout=3)
        response.raise_for_status()  # Raises an exception for 4XX/5XX errors
        data = response.json()

        if data.get("status") == "success":
            return {
                "city": data.get("city", "an unknown city"),
                "regionName": data.get("regionName", "an uncharted territory")
            }
        else:
            # API returned "fail" status (e.g. for other reserved ranges not caught above, or other API issues)
            print(f"Geolocation API error for IP {ip_address}: {data.get('message', 'Unknown error from ip-api.com')}")
            return {"city": "parts unknown", "regionName": "a mysterious land"}
    except requests.exceptions.Timeout:
        print(f"Geolocation request timed out for IP {ip_address}")
        return {"city": "a realm beyond reach", "regionName": "the mists of time"}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching geolocation for IP {ip_address}: {e}")
        return {"city": "a digital realm", "regionName": "the boundless interwebs"}
    except json.JSONDecodeError: # Catching if ip-api.com returns non-JSON
        print(f"Failed to decode JSON from geolocation API for IP {ip_address}")
        return {"city": "a garbled signal", "regionName": "the static void"}
    except Exception as e: # Catch-all for any other unexpected error during API call
        print(f"Generic error in get_geolocation for IP {ip_address} during API call: {e}")
        # Using app.logger for more detailed Flask error logging if configured
        app.logger.error(f"Generic error in get_geolocation for IP {ip_address}: {e}", exc_info=True)
        return {"city": "a place beyond perception", "regionName": "the void"}


# --- Helper Functions (resolve_roll remains the same) ---
def resolve_roll(roll_value, table):
    if not isinstance(table, dict):
        print(f"Warning: Invalid table provided to resolve_roll: {type(table)}")
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
        print(f"Error resolving roll {roll_value}: {e}")
        pass
    return "No result found."

# --- Main Roll Logic & Narrative Logging ---
def get_roll_result_and_log(payload, client_ip=None):
    """Processes roll request, generates result, and logs a narrative entry."""
    geo_info = get_geolocation(client_ip) # geo_info will now use the revised function

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
        print(f"Error processing roll: {e}")
        app.logger.error(f"Error processing roll: {e}", exc_info=True)
        response.update({"status": "error", "errorMessage": f"An internal error occurred processing the roll: {e}"})

    if response["status"] == "success":
        descriptor = random.choice(RANDOM_DESCRIPTORS)
        city = geo_info.get("city", "an undisclosed city")
        region = geo_info.get("regionName", "an unknown region") # Ensure this uses the resolved geo_info
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
        # At this point, 'descriptor', 'city', 'region', 'rolled_value', 
        # 'table_name_for_log', and 'result_for_log' are all defined.

        # Convert result_for_log to a string and strip whitespace for the narrative entry
        result_for_log_str = str(result_for_log).strip()

        # --- START: A/An Logic and new narrative_log_entry construction ---        
        descriptor_words = descriptor.split(' ') #
        if descriptor_words[0].lower() in ["a", "an"]: #
            # If the descriptor itself starts with "a" or "an" (e.g., "an unfortunate soul")
            article_for_narrative = descriptor_words[0].capitalize()
            descriptor_noun_phrase = ' '.join(descriptor_words[1:])
        else:
            # If the descriptor is just the noun phrase (e.g., "wise wizard")
            descriptor_noun_phrase = descriptor
            # Determine "A" or "An" based on the first letter of the noun phrase
            if descriptor_noun_phrase and descriptor_noun_phrase[0].lower() in 'aeiou':
                article_for_narrative = "An"
            else:
                article_for_narrative = "A"
        
        # Construct the narrative log entry using A/An logic and curly double quotes
        narrative_log_entry = f"{article_for_narrative} {descriptor_noun_phrase} from {city}, {region} rolled a {rolled_value} on the {table_name_for_log} table, resulting in: \u201c{result_for_log_str}\u201d" # Curly double quotes “ ”
        
        if response.get("isSecondaryPrompt") and not response.get("secondaryResultText"):
            narrative_log_entry += " (Bonus roll pending...)"
        # --- END: A/An Logic and new narrative_log_entry construction ---

        try:
            log_data_to_store = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "narrative": narrative_log_entry,
                "geo_debug": {"ip": client_ip, "city_resolved": city, "region_resolved": region},
                "raw_payload": payload,
                "raw_response": response
            }
            with open("narrative_dice_log.jsonl", "a", encoding="utf-8") as logfile:
                logfile.write(json.dumps(log_data_to_store) + "\n")
            print(f"NARRATIVE LOG: {narrative_log_entry}")
        except Exception as e:
            app.logger.error(f"Error writing narrative log: {e}", exc_info=True)
            print(f"Error writing narrative log: {e}")

    return response #

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

    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    # Added print statement for debugging IP, you can remove if not needed
    # print(f"--- Attempting geolocation for IP address: {client_ip} ---")
    
    result_data = get_roll_result_and_log(payload, client_ip=client_ip)
    return jsonify(result_data)

@app.route('/share_discord', methods=['POST'])
def share_discord():
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL not set.")
        return jsonify({"status": "error", "error": "Discord webhook URL not configured on server."}), 500
    payload = request.get_json()
    message_content = payload.get('message')
    if not message_content:
        return jsonify({"status": "error", "error": "No message content provided."}), 400
    discord_data = {'content': message_content}
    try:
        response_discord = requests.post(webhook_url, json=discord_data)
        response_discord.raise_for_status()
        print("Message sent to Discord successfully!")
        return jsonify({"status": "success"})
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Discord: {e}")
        return jsonify({"status": "error", "error": f"Failed to send request to Discord: {e}"}), 500
    
# --- Roll History Endpoint (using logs) ---
@app.route('/get_roll_history', methods=['GET'])
def get_roll_history():
    try:
        logs = []
        max_logs_to_return = 50 # Capped at 50

        log_file_path = "narrative_dice_log.jsonl"
        if not os.path.exists(log_file_path):
            return jsonify([]) # Return empty if no log file yet

        with open(log_file_path, "r", encoding="utf-8") as logfile:
            all_lines = logfile.readlines()

        # Get the last 'max_logs_to_return' lines
        recent_lines = all_lines[-max_logs_to_return:]

        for line in recent_lines:
            try:
                log_entry = json.loads(line)
                # Extract only the necessary, safe-to-display information
                # The narrative already contains the anonymized location
                logs.append({
                    "timestamp": log_entry.get("timestamp"),
                    "narrative": log_entry.get("narrative")
                })
            except json.JSONDecodeError:
                print(f"Skipping malformed log line: {line.strip()}") # Or log this error

        # The logs are read from oldest to newest among the recent_lines; reverse for chronological display (newest first)
        return jsonify(list(reversed(logs))) 
    except Exception as e:
        app.logger.error(f"Error reading roll history: {e}", exc_info=True)
        return jsonify({"status": "error", "errorMessage": "Could not retrieve roll history."}), 500

if __name__ == '__main__':
    # For more detailed Flask logging:
    # import logging
    # if not app.debug: # Only configure file logging if not in debug mode
    #    file_handler = logging.FileHandler('flask_prod_errors.log')
    #    file_handler.setLevel(logging.WARNING) # Log WARNING, ERROR, CRITICAL
    #    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    #    file_handler.setFormatter(formatter)
    #    app.logger.addHandler(file_handler)
    #    app.logger.setLevel(logging.WARNING)
    app.run()