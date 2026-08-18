# Crits & Fumbles — Foundry VTT module

Rolls a critical hit or fumble result on the Crits & Fumbles house tables. For the
`dnd5e` system.

Status: **working prototype**, tested on Foundry 14.366 with dnd5e 5.3.3. Automatic
rolling, the chat announcement, the toolbar button, the picker and on-demand rolling
all work. The wording has not had a proper pass.

## Install

### From a manifest URL (no filesystem access needed)

On the Foundry **Setup** screen: **Add-on Modules → Install Module**, then paste this
into the *Manifest URL* field at the bottom of the dialog and click Install:

```
https://github.com/adamwitwer/crits-fumbles/releases/latest/download/module.json
```

Foundry downloads and unpacks it itself, so no server restart is needed. Then open a
`dnd5e` world and enable it in **Game Settings → Manage Modules**.

Note this is *Install Module*, not *Create Module*. Create Module scaffolds a new
empty module on the server and will not fetch this one.

To update later, use Install Module with the same URL again, or Foundry's update
check on the Add-on Modules list.

### By copying files

If you do have filesystem access, copy the `crits-fumbles` folder into `Data/modules/`
so you end up with `Data/modules/crits-fumbles/module.json`, then restart the Foundry
server process — Foundry reads manifests once at startup, so a browser refresh is not
enough for a newly added module.

The folder must be named `crits-fumbles`, matching the `id` in `module.json`.

## Verifying it loaded

Open the browser console (F12) and look for:

```
crits-fumbles v0.7.0 — 13 damage types loaded
Console: CritsFumbles.simulate({ kind: "crit" }) · CritsFumbles.open() · ...
Settings: Game Settings → Configure Settings → Module Settings → Crits & Fumbles
```

**Check that version matches what you expect.** A stale build is the most common cause
of "that function does not exist" or "I cannot find that setting" — both mean the
browser or Foundry is still running an older copy.

After updating the module, **hard-reload the page** (Cmd/Ctrl + Shift + R). Foundry
serves module scripts without cache-busting, so an ordinary refresh can keep running
the previous build.

To check what the running build offers:

```js
game.modules.get("crits-fumbles").version   // installed version
Object.keys(CritsFumbles)                   // available API functions
```

## Where the settings live

**Game Settings** (the gear icon in the sidebar) **→ Configure Settings → Module
Settings → Crits & Fumbles**.

Not under Manage Modules — that page only enables and disables modules.

For a report of which APIs this Foundry build offers, run
`game.modules.get("crits-fumbles").api.probe()`. It exists because Foundry v14 and
dnd5e 5.x are newer than the documentation this was written against.

## Rolling on demand

Click the **burst icon** in the scene control toolbar, up the left-hand side under the
Token tools. It opens the picker with a crit/fumble toggle and the thirteen damage
types, ignoring the turn rule entirely — so it works regardless of whose turn it is, or
whether an attack was made at all. Players see it too; it is the on-demand roll.

If the button is missing, the console says why. Foundry changed the scene control API
in v13, and this module needs the Token control group to exist under that name; the
macro below always works regardless.

### From a macro

Create a **Script** macro with:

```js
game.modules.get("crits-fumbles").api.open();
```

That is the same picker the toolbar button opens.

To skip the dialog and roll a known type directly:

```js
game.modules.get("crits-fumbles").api.roll({ kind: "crit", damageType: "fire" });
```

- `kind` — `"crit"` or `"fumble"`
- `damageType` — one of: bludgeoning, slashing, piercing, acid, cold, fire, lightning,
  thunder, force, necrotic, poison, psychic, radiant

Crits index by damage type directly. Fumbles bucket the same damage types into
`physical` / `elemental` / `magical`, so pass a damage type either way and the module
picks the right table.

## Automatic rolling

On by default. When an attack rolls a natural critical hit or fumble, the module posts
an announcement to chat — a headline, and a dropdown to choose what to roll on:

```
💥 Critical Hit 💥
Damage Type [ Bludgeoning ● ▾ ]  [Roll]
● detected on the attack
```

The attacker's name comes from the chat message's own speaker line above the card,
so the card does not repeat it.

Choosing and rolling posts the result card. Only the player who made the attack, or a
GM, can resolve it, and once resolved the card stops offering the controls.

Announcing in chat rather than opening a dialog keeps the moment visible to the whole
table, leaves a record in the log, and does not steal focus from whoever is mid-turn.

### The house rule

Only a combatant's **first attack of their own turn** is eligible:

- The window is spent by that first attack whether or not it crits. If the first
  attack misses and a second one crits, nothing fires.
- Reactions, opportunity attacks and legendary actions never trigger, since they
  happen on someone else's turn.
- Outside combat there are no turns to track, so everything is eligible. Turn this
  off with the "Trigger outside combat" setting.

To re-open the current turn's window after an undone roll:

```js
game.modules.get("crits-fumbles").api.resetTurn();
```

### Choosing what to roll on

Crits offer the thirteen damage types. **Fumbles offer three categories** — Physical,
Elemental, Magical — which is the coarser split the fumble tables actually use, and
matches the web app.

The module asks rather than deciding because the system frequently cannot know. A
monk's unarmed strike carries both `bludgeoning` and `force` and the player picks per
strike, and that pattern repeats across classes. Guessing would quietly roll the wrong
table. Detected options are marked with ●.

For fumbles, ambiguity is measured in categories: an attack that is both bludgeoning
and piercing is unambiguously Physical, so there is nothing to ask.

Set **Ask for the damage type** to "Only when the attack has more than one damage
type" to skip the prompt for unambiguous weapons, or to "Never ask" to always take the
first type found.

### Condition links

Conditions named in a result — Prone, Stunned, Frightened and nine others — are linked
into the system's own rules compendium, so clicking one opens the rules page beside the
game. The web app sends these to the D&D Beyond glossary in a browser tab; in Foundry
the same rules are already in the world.

The UUIDs are not stored in this module. They are read from
`CONFIG.DND5E.conditionTypes[key].reference` when a card is built, so a system update
cannot leave them pointing at nothing. If the system offers no reference, or the text
enricher is unavailable, the condition stays the plain word it was — the card never
shows raw `@UUID[...]` syntax.

To check the links resolve in your world:

```js
CritsFumbles.checkConditions();
```

That prints a table of each condition, its UUID, and whether it resolves. All twelve
should say true; any false means the rules compendium is missing or not visible to you.

### How it decides

Everything happens on the client that rolled the attack: dnd5e fires its roll hooks
only there, that is where the player who chose the damage type is sitting, and it means
exactly one client posts a card. The one thing that client may not do is write the
Combat flag behind the turn rule, so it asks a GM to record that over a socket.

## Settings

| Setting | Default | Effect |
|---|---|---|
| Roll automatically on a natural crit or fumble | on | Turn off for manual-only rolling |
| Only the first attack of a turn can trigger | on | The house rule. Off = every crit and fumble rolls |
| Ask for the damage type | Always ask | Always / only when ambiguous / never |
| Trigger outside combat | on | Whether crits fire with no active encounter |
| Log attack rolls to the console | off | Diagnostic; prints each attack's shape |

## Testing

Waiting for a natural 20 is a slow way to check a change. Two shortcuts, both as
**Script** macros:

```js
// Run the whole auto-trigger path — turn rule, damage type prompt, chat card —
// against a real weapon on the selected token, without touching the dice.
game.modules.get("crits-fumbles").api.simulate({ kind: "crit" });
game.modules.get("crits-fumbles").api.simulate({ kind: "fumble" });
game.modules.get("crits-fumbles").api.simulate({ kind: "crit", itemName: "Longsword" });
```

```js
// Make every weapon attack by the selected token a critical hit, to exercise the
// genuine dnd5e roll path. Reports whether the flag applied.
game.modules.get("crits-fumbles").api.forceCrits(true);
game.modules.get("crits-fumbles").api.forceCrits(false);   // restore
```

`forceCrits` sets `flags.dnd5e.weaponCriticalThreshold` to 1 — the same flag class
features like Improved Critical use. It modifies the actor, so restore it afterwards
and prefer a test character.

Both are also on the console alias, which is quicker than making a macro:

```js
CritsFumbles.simulate({ kind: "crit" });
CritsFumbles.forceCrits(true);
CritsFumbles.announceTest({ kind: "fumble" });   // post an announcement card directly
```

To take the turn rule out of the picture entirely while working on something else,
turn off **Only the first attack of a turn can trigger** in the module settings.

## What is not built yet

- **A language pass.** Strings are hardcoded rather than localized, terminology drifts
  between "damage type" and "fumble category", and the emoji are placeholders (#21).
- **Removing `probe.js`**, once the remaining UI is written against a confirmed API.

## Regenerating the tables

The data file is generated — do not hand-edit it. Source of truth is `app/*.json` at
the repo root:

```bash
python3 tools/build-foundry-tables.py
```

It validates that every table covers 1–100 with no gaps or overlapping bands, and
refuses to write if anything is wrong.
