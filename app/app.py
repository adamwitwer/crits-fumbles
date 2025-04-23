import os
from flask import Flask, render_template_string, request
import json

app = Flask(__name__)

# Load the crits and fumbles JSON data
json_path = os.path.join(os.path.dirname(__file__), "crits_and_fumbles_v2.json")
with open(json_path) as f:
    DATA = json.load(f)

HTML_TEMPLATE = """
<!doctype html>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Crits & Fumbles</title>
<link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}">
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">

<h1>Crits & Fumbles</h1>
<form method="post" id="main-form">
  <label>Roll Type:</label>
  <select name="roll_type" id="roll_type" onchange="toggleFields()">
    <option value="crit" {% if selected_roll_type == 'crit' %}selected{% endif %}>Critical</option>
    <option value="fumble" {% if selected_roll_type == 'fumble' %}selected{% endif %}>Fumble</option>
  </select><br>

  <div id="crit-fields">
    <label>Damage Type:</label>
    <select name="damage_type" id="damage_type" onchange="toggleMagicDropdown()">
      {% for dt in damage_types if not dt.startswith('magic:') %}
      <option value="{{ dt }}" {% if selected_damage_type == dt %}selected{% endif %}>{{ dt.title() }}</option>
      {% endfor %}
      <option value="magic" {% if selected_damage_type.startswith('magic:') %}selected{% endif %}>Magic</option>
    </select><br>

    <div id="magic-subtype" style="display: none;">
      <label>Type of Magic:</label>
      <select name="magic_subtype">
        {% for dt in damage_types if dt.startswith('magic:') %}
        <option value="{{ dt }}" {% if selected_damage_type == dt %}selected{% endif %}>{{ dt.split(':')[1].title() }}</option>
        {% endfor %}
      </select><br>
    </div>
  </div>

  <input type="hidden" name="roll" id="roll-input">
  <button type="button" onclick="rollDice()">🎲 Roll</button>
</form>

{% if result and not secondary_prompt and not secondary_result %}
  <div class="result-box {% if selected_roll_type == 'fumble' %}fumble{% else %}result{% endif %}">
    <h2>{% if selected_roll_type == 'fumble' %}☠️ Fumble{% else %}🎯 Result{% endif %}</h2>
    <p><strong>You rolled: {{ roll_value }}</strong></p>
    <p>{{ result }}</p>
  </div>
{% endif %}

{% if secondary_prompt %}
  <div class="result-box {% if selected_roll_type == 'fumble' %}fumble{% else %}result{% endif %}">
    <h2>{% if selected_roll_type == 'fumble' %}☠️ Fumble{% else %}🎯 Result{% endif %}</h2>
    <p><strong>You rolled: {{ roll_value }}</strong></p>
    <p>{{ result }}</p>
  </div>
  <form method="post" id="secondary-form">
    <input type="hidden" name="roll_type" value="{{ secondary_type }}">
    <input type="hidden" name="primary_result" value="{{ result }}">
    <input type="hidden" name="primary_roll" value="{{ roll_value }}">
    <input type="hidden" name="roll" id="secondary-roll-input">
    <label>{{ secondary_prompt }}</label><br><br>
    <button type="button" onclick="rollSecondary()">🎲 Roll for Bonus Effect</button>
  </form>
{% endif %}

{% if secondary_result %}
  {% if result %}
  <div class="result-box {% if selected_roll_type == 'fumble' %}fumble{% else %}result{% endif %}">
    <h2>{% if selected_roll_type == 'fumble' %}☠️ Fumble{% else %}🎯 Result{% endif %}</h2>
    <p><strong>You rolled: {{ previous_roll_value }}</strong></p>
    <p>{{ result }}</p>
  </div>
  {% endif %}
  <div class="result-box secondary">
    <h2>✨ Bonus Effect</h2>
    <p><strong>You rolled: {{ roll_value }}</strong></p>
    <p>{{ secondary_result }}</p>
  </div>
{% endif %}

<script>
function rollDice() {
  const rollType = document.getElementById('roll_type').value;
  const max = rollType === 'fumble' ? 100 : 20;
  const roll = Math.floor(Math.random() * max) + 1;
  document.getElementById('roll-input').value = roll;
  document.getElementById('main-form').submit();
}

function rollSecondary() {
  const roll = Math.floor(Math.random() * 20) + 1;
  document.getElementById('secondary-roll-input').value = roll;
  document.getElementById('secondary-form').submit();
}

function toggleFields() {
  const rollType = document.getElementById('roll_type').value;
  document.getElementById('crit-fields').style.display = rollType === 'fumble' ? 'none' : 'block';
}

function toggleMagicDropdown() {
  const damageType = document.getElementById('damage_type').value;
  document.getElementById('magic-subtype').style.display = damageType === 'magic' ? 'block' : 'none';
}

window.onload = function() {
  toggleFields();
  toggleMagicDropdown();

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
                    secondary_prompt = "Roll a d20 for Minor Injury:"
                    secondary_type = "minor"
                elif "major injury" in result.lower():
                    secondary_prompt = "Roll a d20 for Major Injury:"
                    secondary_type = "major"
                elif "insanity" in result.lower():
                    secondary_prompt = "Roll a d20 for Insanity:"
                    secondary_type = "insanity"
            else:
                result = "Invalid damage type."

        elif selected_roll_type == 'fumble' and not result:
            result = resolve_roll(roll_value, DATA['fumbles'])

        elif selected_roll_type in ['minor', 'major', 'insanity']:
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
                                  roll_value=roll_value,
                                  previous_roll_value=previous_roll_value)

if __name__ == '__main__':
    app.run(debug=True)
