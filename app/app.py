from dotenv import load_dotenv
load_dotenv()

import requests
import os
import json
import random
from flask import Flask, render_template, request, jsonify, url_for
import datetime # For timestamps in logs

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
    # ... (your existing load_json function)
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

# --- Geolocation Helper ---
def get_geolocation(ip_address):
    """Fetches city and region for an IP address using ip-api.com."""
    if not ip_address or ip_address == "127.0.0.1": # Handle localhost
        return {"city": "their cozy terminal", "regionName": "the digital ether"}
    try:
        # Request only necessary fields. Free tier allows 45 req/min.
        url = f"http://ip-api.com/json/{ip_address}?fields=status,message,city,regionName,query"
        response = requests.get(url, timeout=2) # 2-second timeout
        response.raise_for_status()  # Raises an exception for 4XX/5XX errors
        data = response.json()

        if data.get("status") == "success":
            return {
                "city": data.get("city", "an unknown city"),
                "regionName": data.get("regionName", "an uncharted territory")
            }
        else:
            print(f"Geolocation API error for IP {ip_address}: {data.get('message', 'Unknown error')}")
            return {"city": "parts unknown", "regionName": "a mysterious land"}
    except requests.exceptions.Timeout:
        print(f"Geolocation request timed out for IP {ip_address}")
        return {"city": "a realm beyond reach", "regionName": "the mists of time"}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching geolocation for IP {ip_address}: {e}")
        return {"city": "a digital realm", "regionName": "the boundless interwebs"}
    except Exception as e: # Catch other potential errors like JSONDecodeError
        print(f"Generic error in get_geolocation for IP {ip_address}: {e}")
        return {"city": "a place beyond perception", "regionName": "the void"}

# --- Helper Functions (resolve_roll remains the same) ---
def resolve_roll(roll_value, table):
    # ... (your existing resolve_roll function)
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
    geo_info = get_geolocation(client_ip) if client_ip else {"city": "an anonymous user", "regionName": "somewhere out there"}

    # Initialize response structure (as in your original code)
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
    roll_type_from_payload = payload.get('rollType') # This is 'crit', 'fumble', or for secondary: 'minor', 'major', 'insanity'
    damage_type = payload.get('damageType')
    magic_subtype = payload.get('magicSubtype')
    fumble_type_from_payload = payload.get('fumbleType')
    attack_type = payload.get('attackType')

    # --- Core Roll Logic (adapted from your original get_roll_result) ---
    try:
        if roll_context == 'primary':
            if roll_type_from_payload == 'crit':
                response["dieType"] = "d20"; response["numDice"] = 1
                roll_value = random.randint(1, 20); response["rollValue"] = roll_value
                crit_damage_type = magic_subtype if damage_type == 'magic' else damage_type
                crit_damage_type = crit_damage_type.lower().strip() if crit_damage_type else 'slashing'
                table = DATA.get('crit_tables', {}).get(crit_damage_type)
                if table:
                    result_text = resolve_roll(roll_value, table)
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
                        roll_entry = entry.get('roll')
                        if not roll_entry: continue
                        if '-' in roll_entry: low, high = map(int, roll_entry.split('-')); match = low <= roll_value <= high
                        else: match = int(roll_entry) == roll_value
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
            # response["resultText"] already contains primary_result_text from payload via initialization
            secondary_table_key_map = {'minor': 'minor_injuries', 'major': 'major_injuries', 'insanity': 'insanities'}
            secondary_table_key = secondary_table_key_map.get(roll_type_from_payload)
            if secondary_table_key:
                secondary_table = DATA.get(secondary_table_key, {})
                response["secondaryResultText"] = resolve_roll(roll_value, secondary_table)
            else:
                response.update({"status": "error", "errorMessage": f"Invalid secondary roll type: {roll_type_from_payload}"})
        else:
            response.update({"status": "error", "errorMessage": f"Invalid roll context: {roll_context}"})

    except Exception as e:
        print(f"Error processing roll: {e}")
        app.logger.error(f"Error processing roll: {e}", exc_info=True) # More detailed server log
        response.update({"status": "error", "errorMessage": f"An internal error occurred processing the roll: {e}"})
    # --- End Core Roll Logic ---

    # --- Narrative Logging ---
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
                table_name_for_log = f"Critical Hit ({effective_damage_type.title() if effective_damage_type else 'General'})"
                result_for_log = response.get("resultText", "No specific result text.")
            elif roll_type_from_payload == 'fumble':
                if fumble_type_from_payload == 'Questionable Arcana':
                    table_name_for_log = f"Questionable Arcana Fumble ({attack_type})"
                    desc = response.get("description", "")
                    eff = response.get("effect", "")
                    result_for_log = f"{desc} Effect: {eff}".strip()
                else: # Smack Down
                    table_name_for_log = "Smack Down Fumble"
                    result_for_log = response.get("resultText", "No specific result text.")
        elif roll_context == 'secondary':
            table_name_for_log = f"{roll_type_from_payload.title()} Effect" # e.g., "Minor Effect"
            result_for_log = response.get("secondaryResultText", "No specific secondary result.")
            # Optional: add context about the primary roll that led to this
            # primary_trigger = response.get("primaryResultForSecondary", "a previous event")
            # narrative_log_entry = f"Following {primary_trigger}, a {descriptor} in {city}, {region} rolled {rolled_value} for a {table_name_for_log}, receiving: '{result_for_log}'."


        narrative_log_entry = f"A {descriptor} from {city}, {region} rolled a {rolled_value} on the {table_name_for_log} table, resulting in: '{result_for_log}'."
        if response.get("isSecondaryPrompt") and not response.get("secondaryResultText"):
            narrative_log_entry += " (Bonus roll pending...)"


        # Log this narrative string
        try:
            log_data_to_store = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), # UTC timestamp
                "narrative": narrative_log_entry,
                "geo_debug": {"ip": client_ip, "city_resolved": city, "region_resolved": region}, # For your debugging
                "raw_payload": payload, # Optional: for detailed debugging
                "raw_response": response # Optional: for detailed debugging
            }
            # Using JSON Lines format for the log file
            with open("narrative_dice_log.jsonl", "a", encoding="utf-8") as logfile:
                logfile.write(json.dumps(log_data_to_store) + "\n")
            print(f"NARRATIVE LOG: {narrative_log_entry}") # For live server console
        except Exception as e:
            app.logger.error(f"Error writing narrative log: {e}", exc_info=True)
            print(f"Error writing narrative log: {e}")

    return response


# --- Routes ---
@app.route('/', methods=['GET'])
def index():
    # ... (your existing index route)
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
    # Call the combined function
    result_data = get_roll_result_and_log(payload, client_ip=client_ip)
    return jsonify(result_data)

@app.route('/share_discord', methods=['POST'])
def share_discord():
    # ... (your existing Discord sharing function)
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


if __name__ == '__main__':
    # For more detailed Flask logging, you can configure app.logger
    # import logging
    # handler = logging.FileHandler('flask_app_errors.log')
    # handler.setLevel(logging.ERROR) # Log only ERROR and CRITICAL messages from Flask
    # app.logger.addHandler(handler)
    app.run(debug=True) # debug=False for production