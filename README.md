# Crits & Fumbles

A Flask web app for rolling critical hits and fumbles in Dungeons & Dragons 5e. Choose a table source, pick your damage or attack type, and roll. A vibe coding project.

**Live at [crits-fumbles.app](https://crits-fumbles.app)**

## Features

- **Four crit table sets**: Fury & Folly (house system), Sterling Vermin, Questionable Arcana, and u/BCoydog
- **Three fumble table sets**: Fury & Folly, Questionable Arcana, and u/BCoydog
- **Damage-type-specific crits**: 13 damage types for Fury & Folly and Sterling Vermin, grouped into optgroup dropdowns (Physical, Elemental, Magic)
- **Condition linking**: D&D conditions (Prone, Stunned, etc.) are hyperlinked to the [2024 Rules Glossary](https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary) on D&D Beyond
- **Discord integration**: Share results to Discord via webhook, with condition links preserved as markdown
- **Roll history**: Chronicles log with narrative descriptions
- **Bonus rolls**: Sterling Vermin crits can trigger secondary rolls for injuries and insanities
- **Dark mode**: Automatic light/dark theme based on system preference
- **Accessible**: Keyboard navigation, focus trapping in modals, ARIA attributes, reduced-motion support

## Sources

| Source | Crits | Fumbles | Die | Notes |
|--------|:-----:|:-------:|:---:|-------|
| **Fury & Folly** | 13 damage types | 3 attack types | d100 | House system; default on load |
| **[Sterling Vermin](https://sterlingvermin.wordpress.com/2016/09/27/critical-hits-revisited/)** | 13 damage types | -- | d20 | By Benjamin Huffman; includes injury/insanity bonus rolls |
| **[Questionable Arcana](https://growupandgame.com/dungeons-and-dragons/questionable-arcana/dnd-5e-crit-confirmed-critical-hit-charts-and-fumble-charts/)** | Weapon, Spell | Weapon, Magic | d100 | Narrative-driven effects |
| **[u/BCoydog](https://www.reddit.com/r/DnD/comments/1cuzgxf/critical_hit_fumble_d100_tables_with_51_results/)** | Melee, Ranged, Magic | Melee, Ranged, Magic | d100 | Community tables from r/DnD |

## Running Locally

1. Clone the repo and `cd` into it.
2. Create a `.env` file:

```
FLASK_APP=app.app
FLASK_ENV=development
FLASK_DEBUG=1
```

3. Set up and run:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask run
```

The app runs at `http://127.0.0.1:5000`.

## Tech Stack

- **Backend**: Flask, Gunicorn, Python 3.13
- **Frontend**: Vanilla JS (ES modules), DOMPurify
- **Hosting**: Render.com
- **Data**: JSON flat files for crit/fumble tables, JSONL for roll history

## Project Structure

```
app/
  app.py                    # Flask routes and roll logic
  security_utils.py         # Rate limiting, IP redaction, CSRF
  critical_hits_master.json # All crit tables (keyed by source)
  fumbles_master.json       # All fumble tables (keyed by source)
  templates/
    index.html              # Single-page Jinja2 template
  static/
    style.css               # All styles including dark mode
    js/
      main.js               # Roll handling, UI updates, Discord sharing
      forms.js              # Dropdown and form state management
      config.js             # Source definitions, optgroups, info texts
      utils.js              # Dice animation, keyword formatting, condition links
      modals.js             # Info, history, and webhook modal logic
      audio.js              # Mute button
      webhook.js            # Discord webhook configuration (WebhookManager)
      purify.min.js         # DOMPurify 3.2.6
```

## Discord Integration

Click the Discord button in the footer to configure sharing:

1. Paste a Discord webhook URL and click "Save & Generate Link"
2. A shareable URL is generated (webhook encoded in the URL fragment)
3. Anyone with that URL can share roll results to the configured Discord channel
4. Condition links are preserved as clickable markdown in Discord messages

## Smack Down

_Deprecated. The Smack Down table has been removed for now, but may return someday!_

The first fumbles table used in the campaign wasn't a fumble table at all. It was the "Smack Down Table" or the "shit happens list," which can only be found on [DeviantArt](https://www.deviantart.com/pandabarbear/art/The-New-Smack-Down-Table-518745000). PandaBarBear notes it's "based on Hack Masters Expanded smart ass smack down table."

A more likely source is [issue 128 of "Knights of the Dinner Table,"](https://kenzerco.com/product/knights-of-the-dinner-table-128/) which includes "The EXPANDED Smart Ass Smack Down Table" on page 41, created for DMs to punish disruptive players:

> Guaranteed to make your players wet themselves in fright, or at least make you feel more like an evil over-lord punishing insubordinates.
