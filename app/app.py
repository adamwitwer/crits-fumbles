from dotenv import load_dotenv
load_dotenv()

import requests
import os
import json
import random
from flask import Flask, render_template, request, jsonify, url_for # Add render_template

app = Flask(__name__)

# --- Load Data ---
def load_json(filename):
    json_path = os.path.join(os.path.dirname(__file__), filename)
    try:
        with open(json_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_path}")
        return {} # Return empty dict on error
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_path}")
        return {}

DATA = load_json("crits_and_fumbles_v2.json")
ARCANA = load_json("fumbles_arcana.json")
# Basic check if data loaded
if not DATA.get('crit_tables') or not DATA.get('fumbles'):
    print("Warning: Core data from crits_and_fumbles_v2.json might be missing.")
if not ARCANA:
     print("Warning: Arcana data from fumbles_arcana.json might be missing.")


# --- Helper Functions ---
def resolve_roll(roll_value, table):
    """Finds the result text for a given roll value in a table."""
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
        pass # Keep trying other keys if possible
    return "No result found."

def get_roll_result(payload):
    """Processes roll request data and returns result dictionary."""
    roll_context = payload.get('rollContext', 'primary') # 'primary' or 'secondary'
    roll_type = payload.get('rollType') # crit, fumble, minor, major, insanity
    damage_type = payload.get('damageType')
    magic_subtype = payload.get('magicSubtype')
    fumble_type = payload.get('fumbleType')
    attack_type = payload.get('attackType')
    primary_result_text = payload.get('primaryResultText', None) # Used when rolling secondary
    primary_roll_value = payload.get('primaryRollValue', None)   # Used when rolling secondary

    response = {
        "status": "success",
        "rollValue": None,
        "resultText": None,
        "description": None, # For Arcana
        "effect": None,      # For Arcana
        "isSecondaryPrompt": False,
        "secondaryPromptText": None,
        "secondaryType": None,
        "primaryRollValueForSecondary": primary_roll_value,
        "primaryResultForSecondary": primary_result_text,
        "errorMessage": None,
        "selectedRollType": roll_type, # Pass back for potential UI use
        "selectedFumbleType": fumble_type,
        "selectedAttackType": attack_type,
        "numDice": 1, # Default
        "dieType": "d20" # Default
    }

    try:
        if roll_context == 'primary':
            if roll_type == 'crit':
                response["dieType"] = "d20"
                response["numDice"] = 1
                roll_value = random.randint(1, 20)
                response["rollValue"] = roll_value

                # Determine actual damage type (handle magic subtype)
                crit_damage_type = magic_subtype if damage_type == 'magic' else damage_type
                crit_damage_type = crit_damage_type.lower().strip() if crit_damage_type else 'slashing' # default

                table = DATA.get('crit_tables', {}).get(crit_damage_type)
                if table:
                    result_text = resolve_roll(roll_value, table)
                    response["resultText"] = result_text
                    # Check for secondary prompts
                    if isinstance(result_text, str): # Ensure it's a string before lower()
                        if "minor injury" in result_text.lower():
                            response["isSecondaryPrompt"] = True
                            response["secondaryPromptText"] = "Minor Injury!"
                            response["secondaryType"] = "minor"
                        elif "major injury" in result_text.lower():
                            response["isSecondaryPrompt"] = True
                            response["secondaryPromptText"] = "Major Injury!"
                            response["secondaryType"] = "major"
                        elif "insanity" in result_text.lower():
                            response["isSecondaryPrompt"] = True
                            response["secondaryPromptText"] = "Insanity!"
                            response["secondaryType"] = "insanity"
                else:
                    response["status"] = "error"
                    response["errorMessage"] = f"Invalid damage type: {crit_damage_type}"

            elif roll_type == 'fumble':
                response["dieType"] = "d10" # Fumbles use d10s
                response["numDice"] = 2 # Fumbles use two d10s
                # Roll d100 for fumbles
                roll_value = random.randint(1, 100)
                response["rollValue"] = roll_value

                if fumble_type == 'Questionable Arcana':
                    attack_type_map = {"Weapon": "Weapon Attack", "Magic": "Spell Attack"}
                    attack_key = attack_type_map.get(attack_type, "Weapon Attack")
                    fumble_list = ARCANA.get(attack_key, [])
                    found_arcana = False
                    for entry in fumble_list:
                        roll_entry = entry.get('roll')
                        if not roll_entry: continue
                        if '-' in roll_entry:
                            low, high = map(int, roll_entry.split('-'))
                            if low <= roll_value <= high:
                                response["description"] = entry.get('description', 'N/A')
                                response["effect"] = entry.get('effect', 'N/A')
                                found_arcana = True
                                break
                        elif int(roll_entry) == roll_value:
                            response["description"] = entry.get('description', 'N/A')
                            response["effect"] = entry.get('effect', 'N/A')
                            found_arcana = True
                            break
                    if not found_arcana:
                        response["description"] = "No matching fumble found."
                        response["effect"] = "No additional effect."
                else: # Smack Down Fumble
                    fumble_table = DATA.get('fumbles', {})
                    response["resultText"] = resolve_roll(roll_value, fumble_table)

            else:
                response["status"] = "error"
                response["errorMessage"] = f"Invalid primary roll type: {roll_type}"

        elif roll_context == 'secondary':
            response["dieType"] = "d20" # Injury/Insanity rolls are d20
            response["numDice"] = 1
            roll_value = random.randint(1, 20)
            response["rollValue"] = roll_value
            response["resultText"] = primary_result_text # Keep primary result text
            response["primaryRollValueForSecondary"] = primary_roll_value

            secondary_table_key = ""
            if roll_type == 'minor': secondary_table_key = 'minor_injuries'
            elif roll_type == 'major': secondary_table_key = 'major_injuries'
            elif roll_type == 'insanity': secondary_table_key = 'insanities'

            if secondary_table_key:
                secondary_table = DATA.get(secondary_table_key, {})
                response["secondaryResultText"] = resolve_roll(roll_value, secondary_table) # Store secondary result separately
            else:
                 response["status"] = "error"
                 response["errorMessage"] = f"Invalid secondary roll type: {roll_type}"

        else:
             response["status"] = "error"
             response["errorMessage"] = f"Invalid roll context: {roll_context}"

    except Exception as e:
        print(f"Error processing roll: {e}") # Log the error server-side
        response["status"] = "error"
        response["errorMessage"] = f"An internal error occurred: {e}"

    return response


# --- Routes ---
@app.route('/', methods=['GET'])
def index():
    """Render the main page."""
    initial_damage_type = "slashing"
    crit_tables = DATA.get('crit_tables', {})
    damage_types_list = sorted(crit_tables.keys()) if crit_tables else []

    # Use render_template instead of render_template_string
    return render_template('index.html', # <-- Name of the file in 'templates' folder
                          damage_types=damage_types_list,
                          selected_damage_type=initial_damage_type,
                          selected_roll_type="crit",
                          selected_fumble_type="Smack Down",
                          selected_attack_type="Weapon"
                          )

@app.route('/roll', methods=['POST'])
def roll_ajax():
    """Handle AJAX roll requests."""
    payload = request.get_json()
    if not payload:
        return jsonify({"status": "error", "errorMessage": "Invalid request data."}), 400

    result_data = get_roll_result(payload)
    return jsonify(result_data)

@app.route('/share_discord', methods=['POST'])
def share_discord():
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL') # Get URL securely
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL not set.")
        return jsonify({"status": "error", "error": "Discord webhook URL not configured on server."}), 500

    payload = request.get_json()
    message_content = payload.get('message')

    if not message_content:
        return jsonify({"status": "error", "error": "No message content provided."}), 400

    # Prepare data for Discord webhook
    discord_data = {
        'content': message_content,
        # 'username': 'Crit & Fumble Roller' # Optional: Customize bot name for this message
        # 'avatar_url': 'URL_TO_AVATAR_IMAGE' # Optional: Customize avatar
    }

    try:
        response = requests.post(webhook_url, json=discord_data)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        if response.status_code == 204: # Discord usually returns 204 No Content on success
            print("Message sent to Discord successfully!")
            return jsonify({"status": "success"})
        else:
             # This might not be reached due to raise_for_status, but good for clarity
            print(f"Failed to send message to Discord, Status Code: {response.status_code}")
            return jsonify({"status": "error", "error": f"Discord API returned status {response.status_code}"}), 500

    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Discord: {e}")
        return jsonify({"status": "error", "error": f"Failed to send request to Discord: {e}"}), 500

# --- HTML Template (String) ---
# (Will be inserted below)

if __name__ == '__main__':
    app.run(debug=True)