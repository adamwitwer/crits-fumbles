# Crits & Fumbles

Rolling critical hits and fumbles in Dungeons & Dragons 5e. A vibe coding project.

Two things live here:

- **[The web app](#the-web-app)** — a Flask site with seven table sets, at
  **[crits-fumbles.app](https://crits-fumbles.app)**. Choose a source, pick your damage
  or attack type, and roll.
- **[The Foundry VTT module](#the-foundry-vtt-module)** — the house tables, ported into
  the virtual tabletop, where a natural 20 announces itself in chat and rolls without
  anyone leaving the game.

## The web app

### Features

- **Four crit table sets**: Fury & Folly (house system), Sterling Vermin, Questionable Arcana, and u/BCoydog
- **Three fumble table sets**: Fury & Folly, Questionable Arcana, and u/BCoydog
- **Damage-type-specific crits**: 13 damage types for Fury & Folly and Sterling Vermin, grouped into optgroup dropdowns (Physical, Elemental, Magic)
- **Condition linking**: D&D conditions (Prone, Stunned, etc.) are hyperlinked to the [2024 Rules Glossary](https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary) on D&D Beyond
- **Discord integration**: Share results to Discord via webhook, with condition links preserved as markdown
- **Roll history**: Chronicles log with narrative descriptions
- **Bonus rolls**: Sterling Vermin crits can trigger secondary rolls for injuries and insanities
- **Dark mode**: Automatic light/dark theme based on system preference
- **Accessible**: Keyboard navigation, focus trapping in modals, ARIA attributes, reduced-motion support

### Sources

| Source | Crits | Fumbles | Die | Notes |
|--------|:-----:|:-------:|:---:|-------|
| **Fury & Folly** | 13 damage types | 3 attack types | d100 | House system; default on load |
| **[Sterling Vermin](https://sterlingvermin.wordpress.com/2016/09/27/critical-hits-revisited/)** | 13 damage types | -- | d20 | By Benjamin Huffman; includes injury/insanity bonus rolls |
| **[Questionable Arcana](https://growupandgame.com/dungeons-and-dragons/questionable-arcana/dnd-5e-crit-confirmed-critical-hit-charts-and-fumble-charts/)** | Weapon, Spell | Weapon, Magic | d100 | Narrative-driven effects |
| **[u/BCoydog](https://www.reddit.com/r/DnD/comments/1cuzgxf/critical_hit_fumble_d100_tables_with_51_results/)** | Melee, Ranged, Magic | Melee, Ranged, Magic | d100 | Community tables from r/DnD |

### Running locally

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

See [AGENTS.md](AGENTS.md) for development notes: how to exercise the app without a test
suite, the invariants worth preserving, and the footguns (notably that the CSP pins a
hash of the inline script in `index.html`).

### Discord integration

Click the Discord button in the footer to configure sharing:

1. Paste a Discord webhook URL and click "Save & Generate Link"
2. A shareable URL is generated (webhook encoded in the URL fragment)
3. Anyone with that URL can share roll results to the configured Discord channel
4. Condition links are preserved as clickable markdown in Discord messages

### Tech stack

- **Backend**: Flask, Gunicorn, Python 3.13
- **Frontend**: Vanilla JS (ES modules), DOMPurify
- **Hosting**: Render.com
- **Data**: JSON flat files for crit/fumble tables, JSONL for roll history

## The Foundry VTT module

Lives in [`foundry/crits-fumbles/`](foundry/crits-fumbles/), with its own
[README](foundry/crits-fumbles/README.md) for setup and settings.

Only the **Fury & Folly** tables are ported — they are the house system, and the only
ones we play with — so the module does not name them. It is just Crits & Fumbles.

- **Rolls itself.** A natural crit or fumble on an attack posts a card to chat with a
  dropdown, and the player picks what to roll on. It asks rather than guessing, because
  the system frequently cannot know: a monk's unarmed strike carries both bludgeoning
  and force, and the player chooses per strike.
- **Knows the house rule.** Only a combatant's first attack of their own turn can
  trigger, and that first attack spends the window whether or not it hits. Reactions and
  legendary actions never fire. All of it is a setting.
- **Links the conditions.** Prone, Stunned and ten others resolve into the system's own
  rules compendium, so a click opens the rules beside the game rather than a browser tab.
- **Rolls on demand.** A burst icon in the scene control toolbar opens the picker for
  anyone, ignoring the turn rule entirely.

### Installing it

On the Foundry **Setup** screen: **Add-on Modules → Install Module**, and paste this
into the *Manifest URL* field:

```
https://github.com/adamwitwer/crits-fumbles/releases/latest/download/module.json
```

No filesystem access to the server is needed.

### Building a release

```bash
./tools/package-foundry-module.sh            # regenerate, check, and zip
./tools/package-foundry-module.sh --release  # and publish it to GitHub
```

The build regenerates `data/tables.json` from `app/*.json`, so the module cannot ship
tables that have drifted from the web app's, and it runs the checks below before
zipping.

### Checking it

```bash
node tools/check-foundry-module.mjs
```

Six suites over the parts that decide things — table lookups, damage type detection,
the turn rule, condition linking, the toolbar registration, and localization coverage —
with a stub standing in for `game` and `CONFIG`.

This is not full coverage and is not meant to be. Anything needing a real canvas,
socket, chat log or document is verified by hand in a world, and the module's
[README](foundry/crits-fumbles/README.md) says which parts those are. What these do
cover is the logic that has actually held bugs: a damage type priority that rolled fire
for a flame tongue's slash, and two names for the same three fumble categories.

## Project structure

```
app/                          # The Flask web app
  app.py                      # Routes and roll logic
  security_utils.py           # Rate limiting, IP redaction, geolocation caching
  critical_hits_master.json   # All crit tables (keyed by source)
  fumbles_master.json         # All fumble tables (keyed by source)
  templates/index.html        # Single-page Jinja2 template
  static/
    style.css                 # All styles including dark mode
    js/
      main.js                 # Roll handling, UI updates, Discord sharing
      forms.js                # Dropdown and form state management
      config.js               # Source definitions, optgroups, info texts
      utils.js                # Dice animation, keyword formatting, condition links
      modals.js               # Info, history, and webhook modal logic
      audio.js                # Mute button
      webhook.js              # Discord webhook configuration (WebhookManager)
      purify.min.js           # DOMPurify 3.2.6

foundry/
  crits-fumbles/              # The Foundry module, as installed
    module.json               # Manifest: version, compatibility, download URL
    lang/en.json              # Every user-facing string
    data/tables.json          # Generated — do not hand-edit
    scripts/
      module.js               # Settings, the public API, wiring
      trigger.js              # Reacts to dnd5e.rollAttack
      turn-gate.js            # The first-attack-of-a-turn house rule
      damage-type.js          # What damage type did this attack deal?
      announce.js             # The chat card and its dropdown
      roller.js               # Rolls a table and posts the result
      conditions.js           # Condition links into the rules compendium
      controls.js             # The scene control toolbar button
      tables.js               # Table lookup, labels, categories
      testing.js              # simulate / forceCrits / watchAttacks
      apps/damage-prompt.js   # The picker dialog
  releases/                   # Build output, also served as a fallback manifest

tools/
  build-foundry-tables.py     # app/*.json -> foundry data/tables.json
  package-foundry-module.sh   # Regenerate, check, zip, optionally publish
  check-foundry-module.mjs    # Run the module's checks
  checks/                     # The suites themselves
```

## Notes
### Smack Down

_Deprecated. The Smack Down table has been removed for now, but may return someday!_

The first fumbles table used in this app wasn't a fumbles table at all. It was the "Smack Down Table" or the "shit happens list," which can only be found on [DeviantArt](https://www.deviantart.com/pandabarbear/art/The-New-Smack-Down-Table-518745000). PandaBarBear notes it's "based on Hack Masters Expanded smart ass smack down table."

A more likely source is [issue 128 of "Knights of the Dinner Table,"](https://kenzerco.com/product/knights-of-the-dinner-table-128/) which includes "The EXPANDED Smart Ass Smack Down Table" on page 41, created for DMs to punish disruptive players:

> Guaranteed to make your players wet themselves in fright, or at least make you feel more like an evil over-lord punishing insubordinates.
