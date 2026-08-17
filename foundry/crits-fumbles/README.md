# Crits & Fumbles — Foundry VTT module

Rolls a critical hit or fumble result on the Crits & Fumbles house tables. For the
`dnd5e` system.

Status: **prototype.** Automatic rolling and manual rolling both work. No dialog yet —
on-demand rolls go through a macro.

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
crits-fumbles | ready — 13 damage types loaded
crits-fumbles | environment probe
```

The probe prints a table of which APIs this Foundry build offers. It exists because
Foundry v14 and dnd5e 5.x are newer than the documentation this was written against;
it will be removed once the remaining features are written.

## Rolling manually

Create a **Script** macro with:

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

### How it decides

dnd5e fires its roll hooks only on the client that made the roll, so a player's attack
never reaches the GM's client, and players cannot write the Combat flag the turn gate
uses. The rolling client therefore reports the attack over a socket and a single GM
client decides and posts, which keeps the gate authoritative and produces exactly one
card.

## Settings

| Setting | Default | Effect |
|---|---|---|
| Roll automatically on a natural crit or fumble | on | Turn off for manual-only rolling |
| Trigger outside combat | on | Whether crits fire with no active encounter |
| Log attack rolls to the console | off | Diagnostic; prints each attack's shape |

## What is not built yet

- **A roll dialog**, scene-control button, and keybinding. On-demand rolling works
  through the macro above.
- **Condition links** into the rules compendium.

## Regenerating the tables

The data file is generated — do not hand-edit it. Source of truth is `app/*.json` at
the repo root:

```bash
python3 tools/build-foundry-tables.py
```

It validates that every table covers 1–100 with no gaps or overlapping bands, and
refuses to write if anything is wrong.
