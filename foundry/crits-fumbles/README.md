# Crits & Fumbles — Foundry VTT module

Rolls a critical hit or fumble result on the Crits & Fumbles house tables. For the
`dnd5e` system.

Status: **prototype.** Automatic rolling, the damage type picker and on-demand rolling
all work. Not yet wired to a scene-control button or keybinding.

## Install

### From a manifest URL (no filesystem access needed)

On the Foundry **Setup** screen: **Add-on Modules → Install Module**, then paste this
into the *Manifest URL* field at the bottom of the dialog and click Install:

```
https://raw.githubusercontent.com/adamwitwer/crits-fumbles/main/foundry/releases/module.json
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
crits-fumbles | init
crits-fumbles | ready — v0.4.0, 13 damage types loaded
```

Check the version in that line matches what you installed — two builds are otherwise
indistinguishable in the console.

For a report of which APIs this Foundry build offers, run
`game.modules.get("crits-fumbles").api.probe()`. It exists because Foundry v14 and
dnd5e 5.x are newer than the documentation this was written against.

## Rolling on demand

Create a **Script** macro with:

```js
game.modules.get("crits-fumbles").api.open();
```

That opens the picker with a crit/fumble toggle and the thirteen damage types. It
ignores the turn rule entirely, so it works regardless of whose turn it is or whether
an attack was made at all. Give this one to players.

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

On by default. When an attack rolls a natural critical hit or fumble, the matching
table is rolled and posted to chat.

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

### Choosing the damage type

The module asks which damage type to roll on, with the types it detected on the attack
highlighted. Picking one rolls immediately.

It asks rather than deciding because the system frequently cannot know. A monk's
unarmed strike carries both `bludgeoning` and `force` and the player picks per strike,
and that pattern repeats across classes. Guessing would quietly roll the wrong table.

Set **Ask for the damage type** to "Only when the attack has more than one damage
type" to skip the prompt for unambiguous weapons, or to "Never ask" to always take the
first type found.

### How it decides

Everything happens on the client that rolled the attack: dnd5e fires its roll hooks
only there, that is where the player who chose the damage type is sitting, and it means
exactly one client posts a card. The one thing that client may not do is write the
Combat flag behind the turn rule, so it asks a GM to record that over a socket.

## Settings

| Setting | Default | Effect |
|---|---|---|
| Roll automatically on a natural crit or fumble | on | Turn off for manual-only rolling |
| Ask for the damage type | Always ask | Always / only when ambiguous / never |
| Trigger outside combat | on | Whether crits fire with no active encounter |
| Log attack rolls to the console | off | Diagnostic; prints each attack's shape |

## What is not built yet

- **A scene-control button and keybinding.** On-demand rolling works through the macro
  above.
- **Condition links** into the rules compendium.

## Regenerating the tables

The data file is generated — do not hand-edit it. Source of truth is `app/*.json` at
the repo root:

```bash
python3 tools/build-foundry-tables.py
```

It validates that every table covers 1–100 with no gaps or overlapping bands, and
refuses to write if anything is wrong.
