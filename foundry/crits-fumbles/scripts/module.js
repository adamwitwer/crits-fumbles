import { promptForDamageType } from "./apps/damage-prompt.js";
import { registerAnnouncementListeners } from "./announce.js";
import { MODULE_ID } from "./constants.js";
import { runProbe, watchAttacks } from "./probe.js";
import { rollTable } from "./roller.js";
import { announceTest, forceCrits, simulate } from "./testing.js";
import { registerTrigger } from "./trigger.js";
import { categoryFor, damageTypes, loadTables, resolveRoll } from "./tables.js";
import { resetWindow } from "./turn-gate.js";

Hooks.once("init", () => {
  console.log(`${MODULE_ID} | init`);

  game.settings.register(MODULE_ID, "autoTrigger", {
    name: "Roll automatically on a natural crit or fumble",
    hint: "When off, the tables are only rolled on demand.",
    scope: "world",
    config: true,
    type: Boolean,
    default: true
  });

  game.settings.register(MODULE_ID, "promptDamageType", {
    name: "Ask for the damage type",
    hint: "The system often cannot tell: a monk's unarmed strike is both bludgeoning and force, and the player chooses per strike.",
    scope: "world",
    config: true,
    type: String,
    choices: {
      always: "Always ask",
      ambiguous: "Only when the attack has more than one damage type",
      never: "Never ask — use the first type found"
    },
    default: "always"
  });

  game.settings.register(MODULE_ID, "firstAttackOnly", {
    name: "Only the first attack of a turn can trigger",
    hint: "The house rule. The window is spent by that first attack whether or not it crits, and reactions never trigger. Turn off to let every crit and fumble roll.",
    scope: "world",
    config: true,
    type: Boolean,
    default: true
  });

  game.settings.register(MODULE_ID, "outsideCombat", {
    name: "Trigger outside combat",
    hint: "With no active encounter there are no turns to track, so every crit or fumble is eligible.",
    scope: "world",
    config: true,
    type: Boolean,
    default: true
  });

  game.settings.register(MODULE_ID, "debugAttacks", {
    name: "Log attack rolls to the console",
    hint: "Diagnostic only. Prints the shape of each attack roll.",
    scope: "world",
    config: true,
    type: Boolean,
    default: false
  });
});

Hooks.once("ready", async () => {
  let tableStatus;
  try {
    await loadTables();
    tableStatus = `${damageTypes().length} damage types loaded`;
  } catch (error) {
    tableStatus = `FAILED: ${error.message}`;
    console.error(`${MODULE_ID} |`, error);
  }

  // The public surface. Macros and the trigger both go through this.
  game.modules.get(MODULE_ID).api = {
    open: openPrompt,
    roll: rollTable,
    resetTurn: resetWindow,
    simulate,
    announceTest,
    forceCrits,
    damageTypes,
    categoryFor,
    resolveRoll,
    probe: runProbe
  };

  // Registered here rather than in init so game.socket is definitely connected.
  registerTrigger();
  registerAnnouncementListeners();

  if (game.settings.get(MODULE_ID, "debugAttacks")) watchAttacks();

  // Console alias. Typing the full game.modules.get(...) chain to test something is
  // tedious, and a missing name here is the quickest way to spot a stale build.
  globalThis.CritsFumbles = game.modules.get(MODULE_ID).api;

  const version = game.modules.get(MODULE_ID)?.version ?? "unknown";
  console.log(
    `%c${MODULE_ID} v${version}%c — ${tableStatus}\n` +
    `Console: CritsFumbles.simulate({ kind: "crit" }) · CritsFumbles.open() · CritsFumbles.forceCrits(true)\n` +
    `Settings: Game Settings → Configure Settings → Module Settings → Crits & Fumbles`,
    "font-weight:bold", "font-weight:normal"
  );
});

/**
 * On-demand roll. Unlike the trigger this ignores the turn gate entirely, so it works
 * regardless of whose turn it is or whether an attack was made at all.
 */
async function openPrompt({ kind = "crit", actor = null, lockKind = false } = {}) {
  const choice = await promptForDamageType({ kind, actorName: actor?.name ?? null, lockKind });
  if (!choice?.damageType) return null;
  return rollTable({ kind: choice.kind, damageType: choice.damageType, actor });
}
