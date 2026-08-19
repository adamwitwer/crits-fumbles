# Crits & Fumbles — Foundry VTT module

Rolls a critical hit or fumble result on the Crits & Fumbles house tables. For the
`dnd5e` system.

Status: **working prototype**, tested on Foundry 14.366 with dnd5e 5.3.3. Automatic
rolling, the chat announcement, the toolbar button, the picker, condition links and
on-demand rolling all work.

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
crits-fumbles v0.8.0 — 13 damage types loaded
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

### How often it can trigger

**When a crit or fumble can trigger** offers three rules:

| Setting | Behaviour |
|---|---|
| **Only on the turn's first attack roll** | The original house rule, and the default. The turn's opening attack spends it whatever that roll was — an ordinary 12 on the first swing means a natural 20 on the second does nothing. |
| **Once each turn, on any attack** | Still one per turn, but the turn is spent by whatever actually fires. Miss with the first attack, crit with the third, and it rolls. |
| **Every crit and fumble** | No limit. Several in one turn all fire, and so do reactions, opportunity attacks and legendary actions. |

Under the two limited rules, reactions and legendary actions never trigger: they land on
someone else's turn, and only the creature whose turn it is is ever eligible.

The module reads the die, not the target's AC, so it never knows whether an attack hit.
"First attack roll" means exactly that.

**Trigger outside combat** is a separate question, asked first and whichever limit is
set. With no encounter running there are no turns to track — and an attack out of
combat rolls initiative anyway, which starts one.

To re-open the current turn after an undone roll:

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
| When a crit or fumble can trigger | Turn's first attack | First attack / once each turn / every one |
| Ask for the damage type | Always ask | Always / only when ambiguous / never |
| Trigger outside combat | on | Applies whichever limit is set |
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
features like Improved Critical use. That flag lives on the actor in the **world
database on the server**, not in the browser, so it survives a refresh and follows the
character to any machine. A test flag left on overnight looks exactly like a module
bug the next day, which is why setting it raises a warning you have to dismiss.

The way back, when you no longer remember which character you used:

```js
CritsFumbles.clearForcedCrits({ dryRun: true });   // look first
CritsFumbles.clearForcedCrits();                   // then clear
```

It sweeps every actor and every unlinked scene token, and prints a table of everything
carrying a crit threshold with what it did about each. **It only clears the value 1.**
A Champion Fighter stores 19 or 18 in the same flag for Improved Critical, and those
are reported as left alone rather than stripped.

Everything is also on the console alias, which is quicker than making a macro:

```js
CritsFumbles.simulate({ kind: "crit" });
CritsFumbles.forceCrits(true);
CritsFumbles.announceTest({ kind: "fumble" });   // post an announcement card directly
CritsFumbles.turnStatus();                       // would the selected token trigger now?
```

To take the turn rule out of the picture entirely while working on something else, set
**When a crit or fumble can trigger** to "Every crit and fumble".

### Walking an encounter

The turn rule is the one part that only behaves like itself inside a running combat,
so it is worth walking an encounter deliberately once.

Building one, from the Actors sidebar:

1. Drag the actors onto a scene to place tokens.
2. Select them all — drag a marquee, or shift-click each one.
3. Right-click any selected token and click the crossed swords on the token HUD. That
   adds every selected token to the Combat Tracker at once.
4. Open the Combat Tracker (crossed swords in the sidebar tabs) and click **Roll All**.
5. Click **Begin Combat**. The arrows at the top step through turns and rounds.

Then, at each turn, select the token whose turn it is and ask:

```js
CritsFumbles.turnStatus();
```

It prints the round and turn, whose turn it actually is, the three settings that feed
the decision, whether this turn's window has already been spent, and an ELIGIBLE or
NOT ELIGIBLE verdict with the reason in plain English. No dice needed — the question
"should this have triggered?" is answerable before rolling anything.

What to look for, with the default "Only on the turn's first attack roll":

| Do this | Expect |
|---|---|
| Select the current combatant, `turnStatus()` | ELIGIBLE — "first attack of their turn" |
| Make any attack, then `turnStatus()` again | NOT ELIGIBLE — "window already spent by an earlier attack this turn" |
| `simulate({ kind: "crit" })` now | Nothing rolls; the console logs the decline and why |
| Select a *different* token, `turnStatus()` | NOT ELIGIBLE — "not their turn (it is X's)" |
| Advance to the next turn, `turnStatus()` | ELIGIBLE again — the window is keyed to `round:turn` |
| `CritsFumbles.resetTurn()` mid-turn | ELIGIBLE again without advancing |

Switch the setting to "Once each turn, on any attack" and the second row changes: a
first attack that does not crit leaves the window open, and only something that
actually fires spends it. That difference between the two limited modes is the whole
reason there are two.

Two things that will look like bugs and are not:

- **A halfling cannot fumble.** Halfling Lucky rerolls a natural 1 inside dnd5e before
  this module ever sees the roll. Use `simulate({ kind: "fumble" })` or a non-halfling.
- **Reactions and opportunity attacks never trigger** under either limited mode. They
  land on someone else's turn, which the gate reports as exactly that.

### Checks that run outside Foundry

```bash
node tools/check-foundry-module.mjs
```

Covers the parts that decide things — table lookups, damage type detection, the
per-turn limits, what actually fires and what spends the turn, condition linking, the
toolbar registration, the forced-crit sweep and localization coverage — against a stub
for `game` and `CONFIG`. `package-foundry-module.sh` runs them before it zips.

**What they do not cover**, and what therefore has to be looked at in a world:

- Whether anything renders. Cards, the picker and the settings panel are only ever
  verified by eye.
- The socket handoff to a GM for the Combat flag write, which needs two clients.
- Whether condition UUIDs resolve here — that is `CritsFumbles.checkConditions()`.
- Which tooltip attribute this Foundry build honours on the toolbar button — that is
  `CritsFumbles.checkTooltip()`. Both `data-tooltip-html` and `data-tooltip` are set,
  so the button reads sensibly either way, but only a hover shows which one won.
- The dnd5e hook itself. The suites call `onAttack` directly; that dnd5e still fires
  `dnd5e.rollAttack` with this signature is only ever proved by making an attack.

## Wording

User-facing text lives in `lang/en.json`, not in the scripts. Changing what a card,
button or setting says is an edit to that one file — there is no English hardcoded in
the render paths, which is enforced by a check rather than by discipline.

Two names are not this module's to choose. Damage types come from
`CONFIG.DND5E.damageTypes[key].label`, so "Bludgeoning" matches the character sheet
rather than being spelled twice, and condition links come from
`CONFIG.DND5E.conditionTypes[key].reference`. The three fumble categories — Physical,
Elemental, Magical — are ours, under `CRITSFUMBLES.Category.*`.

A fumble is rolled by **category**, never by damage type. Any label that says "damage
type" on a fumble is a bug.

## Regenerating the tables

The data file is generated — do not hand-edit it. Source of truth is `app/*.json` at
the repo root:

```bash
python3 tools/build-foundry-tables.py
```

It validates that every table covers 1–100 with no gaps or overlapping bands, and
refuses to write if anything is wrong.
