import os
from flask import Flask, render_template_string, request
import json

app = Flask(__name__)

# Load the crits and fumbles JSON data
json_path = os.path.join(os.path.dirname(__file__), "crits_and_fumbles_v2.json")
with open(json_path) as f:
    DATA = json.load(f)

# Load the Questionable Arcana fumbles JSON data
arcana_path = os.path.join(os.path.dirname(__file__), "fumbles_arcana.json")
with open(arcana_path) as f:
    ARCANA = json.load(f)


HTML_TEMPLATE = """
<!doctype html>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Crits & Fumbles</title>
<link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}">
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Merriweather&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">

<h1>Crits & Fumbles</h1>
<form method="post" id="main-form">
  <div>
    <label for="roll_type">Roll Type</label>
    <select name="roll_type" id="roll_type" onchange="toggleFields()">
      <option value="crit" {% if selected_roll_type == 'crit' %}selected{% endif %}>Critical</option>
      <option value="fumble" {% if selected_roll_type == 'fumble' %}selected{% endif %}>Fumble</option>
    </select>
  </div>

  <div id="fumble-type-container" style="display:none;">
    <label for="fumbleType">Fumble Type:</label>
    <select id="fumbleType" name="fumbleType" onchange="toggleAttackType()">
      <option value="Smack Down" {% if selected_fumble_type == 'Smack Down' %}selected{% endif %}>Smack Down</option>
      <option value="Questionable Arcana" {% if selected_fumble_type == 'Questionable Arcana' %}selected{% endif %}>Questionable Arcana</option>
    </select>
  </div>

  <div id="attack-type-container" style="display:none;">
    <label for="attackType">Attack Type:</label>
    <select id="attackType" name="attackType">
      <option value="Weapon" {% if selected_attack_type == 'Weapon' %}selected{% endif %}>Weapon</option>
      <option value="Magic" {% if selected_attack_type == 'Magic' %}selected{% endif %}>Magic</option>
  </select>
  </div>

  <div id="crit-fields">
    <div>
      <label for="damage_type">Damage Type</label>
      <select name="damage_type" id="damage_type" onchange="toggleMagicDropdown()">
        {% for dt in damage_types if not dt.startswith('magic:') %}
        <option value="{{ dt }}" {% if selected_damage_type == dt %}selected{% endif %}>{{ dt.title() }}</option>
        {% endfor %}
        <option value="magic" {% if selected_damage_type.startswith('magic:') %}selected{% endif %}>Magic</option>
      </select>
    </div>

    <div id="magic-subtype" style="display: none;">
      <label for="magic_subtype">Type of Magic</label>
      <select name="magic_subtype" id="magic_subtype">
        {% for dt in damage_types if dt.startswith('magic:') %}
        <option value="{{ dt }}" {% if selected_damage_type == dt %}selected{% endif %}>{{ dt.split(':')[1].title() }}</option>
        {% endfor %}
      </select>
    </div>
  </div>

  <input type="hidden" name="roll" id="roll-input">
  <button type="button" onclick="rollDice()" aria-label="Roll dice for result">🎲 Roll</button>
</form>

{% if result and not secondary_prompt and not secondary_result %}

    {# Determine the common class and title ONCE #}
    {% set result_class = 'fumble' if selected_roll_type == 'fumble' else 'result' %}
    {% set result_title = '☠️ Fumble' if selected_roll_type == 'fumble' else '🎯 Result' %}

    {# --- Determine die type and number based on context --- #}
    {% set num_dice = 1 %}      {# Default: 1 die #}
    {% set die_type = 'd20' %}  {# Default: d20 for crits #}

    {% if selected_roll_type == 'fumble' %}
        {# ALL Fumbles use two d10s #}
        {% set num_dice = 2 %}
        {% set die_type = 'd10' %}
    {% endif %}
    {# --- Set full image source and alt text based on die_type --- #}
    {% set die_image_filename = die_type + '.png' %}
    {% set die_image_src = url_for('static', filename='img/' + die_image_filename) %}
    {% set die_alt_text = die_type %}


    {# --- Now render the appropriate result box structure --- #}
    {% if description and effect %}
        {# --- Case 1: Questionable Arcana Fumble --- #}
        {# This will now correctly use two d10s #}
        <div class="result-box {{ result_class }}">
          <div class="roll-result">
            {# Show the first d10 #}
            <img src="{{ die_image_src }}" alt="{{ die_alt_text }}" class="inline-die" />
            <span class="roll-value">{{ roll_value }}</span>
            {# Show the second d10 (since num_dice = 2 for fumbles) #}
            <img src="{{ die_image_src }}" alt="{{ die_alt_text }}" class="inline-die" />
          </div>
          <div class="description-box">
            <p>{{ description }}</p>
          </div>
        </div>

        <div class="result-box secondary">
          <h2>Effect</h2>
          <p>{{ effect }}</p>
        </div>

    {% else %}
        {# --- Case 2: Crit (1 x d20) or Smack Down Fumble (2 x d10) --- #}
        <div class="result-box {{ result_class }}">
          <div class="roll-result">
            {# Show the first die (d20 for crit, d10 for fumble) #}
            <img src="{{ die_image_src }}" alt="{{ die_alt_text }}" class="inline-die" />
            <span class="roll-value">{{ roll_value }}</span>
            {# Conditionally show the second die ONLY if num_dice is 2 (i.e., for fumbles) #}
            {% if num_dice == 2 %}
               <img src="{{ die_image_src }}" alt="{{ die_alt_text }}" class="inline-die" />
            {% endif %}
          </div>
          <p>{{ result }}</p>
        </div>
    {% endif %}

{% endif %}

{% if secondary_prompt %}

    {# Determine the common class and title ONCE for this block #}
    {% set result_class = 'fumble' if selected_roll_type == 'fumble' else 'result' %}
    {% set result_title = '☠️ Fumble' if selected_roll_type == 'fumble' else '🎯 Result' %}

    <div class="result-box {{ result_class }}"> {# Use the variable #}
      <div class="roll-result">
            <img src="{{ url_for('static', filename='img/d20.png') }}" alt="d20" class="inline-die" />
            <span class="roll-value">{{ roll_value }}</span>
      </div>
      <p>{{ result }}</p>
      <p class="scroll-note">👇 Bonus Effect!!! 👇</p>
    </div>

    <form method="post" id="secondary-form" class="bonus-alert">
      <input type="hidden" name="roll_type" value="{{ secondary_type }}">
      <input type="hidden" name="primary_result" value="{{ result }}">
      <input type="hidden" name="primary_roll" value="{{ roll_value }}">
      <input type="hidden" name="roll" id="secondary-roll-input">
      <input type="hidden" name="damage_type" value="{{ selected_damage_type }}">
      {% if selected_damage_type.startswith('magic:') %}
        <input type="hidden" name="magic_subtype" value="{{ selected_damage_type }}">
      {% endif %}
      <h2>{{ secondary_prompt }}</h2>
      <button type="button" onclick="rollSecondary()" aria-label="Roll dice for bonus effect">
        🎲 Roll
      </button>
    </form>

{% endif %}

{% if secondary_result %}

  {# --- Conditionally display the Primary Result --- #}
  {% if result %}
    {# Determine class and title for the primary result ONCE #}
    {% set primary_result_class = 'fumble' if selected_roll_type == 'fumble' else 'result' %}
    {% set primary_result_title = '☠️ Fumble' if selected_roll_type == 'fumble' else '🎯 Result' %}

    <div class="result-box {{ primary_result_class }}">  {# Use variable #}
      
      <div class="roll-result">
            <img src="{{ url_for('static', filename='img/d20.png') }}" alt="d20" class="inline-die" />
            <span class="roll-value">{{ previous_roll_value }}</span>
      </div>
      <p>{{ result }}</p>
    </div>
  {% endif %}

  {# --- Always display the Secondary Result --- #}
  <div class="result-box secondary">
    <h2>✨ Bonus Effect</h2>
    <div class="roll-result">
      <img src="{{ url_for('static', filename='img/d20.png') }}" alt="d20" class="inline-die" />
      <span class="roll-value">{{ roll_value }}</span>
    </div>
    <p>{{ secondary_result }}</p>
  </div>

{% endif %}

<footer class="app-footer">
  <p>
    Made with 🎲 by Adam |
    <a href="https://github.com/adamwitwer/crits-fumbles" target="_blank" rel="noopener" aria-label="GitHub Repository">
      <svg class="github-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path fill="currentColor"
          d="M12 0C5.37 0 0 5.373 0 12c0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577v-2.17c-3.338.726-4.033-1.416-4.033-1.416-.546-1.386-1.333-1.756-1.333-1.756-1.09-.745.083-.729.083-.729 1.205.084 1.84 1.237 1.84 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.776.42-1.304.762-1.603-2.665-.305-5.466-1.334-5.466-5.933 0-1.31.47-2.38 1.235-3.22-.124-.303-.535-1.527.117-3.176 0 0 1.008-.322 3.3 1.23.957-.266 1.98-.399 3-.404 1.02.005 2.043.138 3 .404 2.29-1.552 3.296-1.23 3.296-1.23.653 1.649.242 2.873.118 3.176.767.84 1.233 1.91 1.233 3.22 0 4.61-2.804 5.625-5.475 5.922.43.37.823 1.103.823 2.222v3.293c0 .322.218.694.825.576C20.565 21.796 24 17.298 24 12c0-6.627-5.373-12-12-12z" />
      </svg>
    </a>
  </p>
</footer>

<script>
function rollDice() {
  const rollType = document.getElementById('roll_type').value;
  const max = rollType === 'fumble' ? 100 : 20;
  const roll = Math.floor(Math.random() * max) + 1;
  document.getElementById('roll-input').value = roll;
  document.getElementById('main-form').submit();
}

function toggleAttackType() {
  const rollType = document.getElementById('roll_type').value;
  const fumbleType = document.getElementById('fumbleType').value;
  const attackTypeContainer = document.getElementById('attack-type-container');

  if (rollType === 'fumble' && fumbleType === 'Questionable Arcana') {
    attackTypeContainer.style.display = 'block';
  } else {
    attackTypeContainer.style.display = 'none';
  }
}

function rollSecondary() {
  const roll = Math.floor(Math.random() * 20) + 1;
  document.getElementById('secondary-roll-input').value = roll;
  document.getElementById('secondary-form').submit();
}

function toggleFields() {
  const rollType = document.getElementById('roll_type').value;
  const critFields = document.getElementById('crit-fields');
  const fumbleTypeContainer = document.getElementById('fumble-type-container');  // <--- NEW

  if (rollType === 'fumble') {
    critFields.style.display = 'none';
    fumbleTypeContainer.style.display = 'block';  // <--- NEW
  } else {
    critFields.style.display = 'block';
    fumbleTypeContainer.style.display = 'none';   // <--- NEW
  }

  toggleAttackType();
}

function toggleMagicDropdown() {
  const damageType = document.getElementById('damage_type').value;
  document.getElementById('magic-subtype').style.display = damageType === 'magic' ? 'block' : 'none';
}

window.onload = function() {
  toggleFields();
  toggleMagicDropdown();
  toggleAttackType();

  // find the bonus box first, otherwise the primary result
  const el = document.querySelector('.result-box.secondary')
          || document.querySelector('.result-box');
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}
</script>
"""

def resolve_roll(roll, table):
    try:
        val = int(roll)
        for key in table:
            if '-' in key:
                start, end = map(int, key.split('-'))
                if start <= val <= end:
                    return table[key]
            elif str(val) == key:
                return table[key]
    except ValueError:
        pass
    return "No result found."

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    secondary_prompt = None
    secondary_type = None
    secondary_result = None
    selected_damage_type = "slashing"
    selected_roll_type = "crit"
    roll_value = None
    previous_roll_value = None
    selected_fumble_type = "Smack Down"  # Default if not submitted
    attack_type = "Weapon"
    selected_attack_type = attack_type
    description = None
    effect = None

    if request.method == 'POST':
        selected_roll_type = request.form.get('roll_type')
        roll_value = request.form.get('roll')
        if request.form.get('primary_roll'):
            previous_roll_value = request.form.get('primary_roll')
        result = request.form.get('primary_result')  # Preserve primary result for secondary

        if selected_roll_type == 'crit' and not result:
            base_type = request.form.get('damage_type')
            damage_type = request.form.get('magic_subtype') if base_type == 'magic' else base_type
            damage_type = damage_type.lower().strip()
            selected_damage_type = damage_type
            table = DATA['crit_tables'].get(damage_type)
            if table:
                result = resolve_roll(roll_value, table)
                if "minor injury" in result.lower():
                    secondary_prompt = "Minor Injury!"
                    secondary_type = "minor"
                elif "major injury" in result.lower():
                    secondary_prompt = "Major Injury!"
                    secondary_type = "major"
                elif "insanity" in result.lower():
                    secondary_prompt = "Insanity!"
                    secondary_type = "insanity"
            else:
                result = "Invalid damage type."

        elif selected_roll_type == 'fumble' and not result:
            selected_fumble_type = request.form.get('fumbleType', 'Smack Down')
            attack_type = request.form.get('attackType', 'Weapon')

            roll_value_int = int(roll_value)
            
            if selected_fumble_type == 'Questionable Arcana':
                # Lookup Questionable Arcana
                attack_type = attack_type or 'Weapon'
                attack_type_map = {
                    "Weapon": "Weapon Attack",
                    "Magic": "Spell Attack"
                }
                attack_key = attack_type_map.get(attack_type, "Weapon Attack")  # default to Weapon Attack if weird
                fumble_list = ARCANA.get(attack_key, [])

                for entry in fumble_list:
                    roll_entry = entry['roll']
                    if '-' in roll_entry:
                        low, high = map(int, roll_entry.split('-'))
                        if low <= roll_value_int <= high:
                            description = entry['description']
                            effect = entry['effect']
                            result = f"Description: {description}\nEffect: {effect}"
                            break
                    else:
                        if int(roll_entry) == roll_value_int:
                            description = entry['description']
                            effect = entry['effect']
                            result = f"Description: {description}\nEffect: {effect}"
                            break

                else:
                    description = "No matching fumble found."
                    effect = "No additional effect."
                    result = "No matching fumble found."
            else:
                # Normal Smack Down
                result = resolve_roll(roll_value, DATA['fumbles'])

        elif selected_roll_type in ['minor', 'major', 'insanity']:
            base_type = request.form.get('damage_type')
            if base_type:
                damage_type = request.form.get('magic_subtype') if base_type == 'magic' else base_type
                damage_type = damage_type.lower().strip()
                selected_damage_type = damage_type

            secondary_table = DATA[f"{selected_roll_type}_injuries"] if selected_roll_type != 'insanity' else DATA['insanities']
            secondary_result = resolve_roll(roll_value, secondary_table)
            
    return render_template_string(HTML_TEMPLATE,
                              result=result,
                              secondary_prompt=secondary_prompt,
                              secondary_type=secondary_type,
                              secondary_result=secondary_result,
                              damage_types=sorted(DATA['crit_tables'].keys()),
                              selected_damage_type=selected_damage_type,
                              selected_roll_type=selected_roll_type,
                              selected_fumble_type=selected_fumble_type,
                              selected_attack_type=attack_type,
                              roll_value=roll_value,
                              previous_roll_value=previous_roll_value,
                              description=description,
                              effect=effect)

if __name__ == '__main__':
    app.run(debug=True)
