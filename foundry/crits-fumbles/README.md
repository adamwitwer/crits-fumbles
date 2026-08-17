# Crits & Fumbles — Foundry VTT module

Rolls a critical hit or fumble result on the Crits & Fumbles house tables. For the
`dnd5e` system.

Status: **early prototype.** Manual rolling works; the automatic trigger on a natural
crit/fumble is not built yet (see below).

## Install

The module folder must be named `crits-fumbles` — it has to match the `id` in
`module.json` or Foundry ignores it.

1. Copy the `crits-fumbles` folder into your Foundry data directory under
   `Data/modules/`, so you end up with `Data/modules/crits-fumbles/module.json`.
2. Restart the Foundry server process. (Foundry reads `module.json` once at startup;
   a browser refresh is not enough for a new module or a manifest change.)
3. In a `dnd5e` world: **Game Settings → Manage Modules → enable Crits & Fumbles**.

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

## What is not built yet

- **Auto-trigger on a natural crit/fumble.** Reading the damage type off an attack in
  dnd5e 5.x is the one piece that could not be confirmed from documentation, so the
  module currently only *observes* attacks: with the "Log attack rolls" setting on, each
  attack prints its shape to the console. That output is what the trigger will be built
  from.
- **The house rule** limiting auto-rolls to a combatant's first attack per turn.
- **A roll dialog**, scene-control button, and keybinding.
- **Styling** for the chat card.

## Regenerating the tables

The data file is generated — do not hand-edit it. Source of truth is `app/*.json` at
the repo root:

```bash
python3 tools/build-foundry-tables.py
```

It validates that every table covers 1–100 with no gaps or overlapping bands, and
refuses to write if anything is wrong.
