import { MODULE_ID } from "./constants.js";
import { runProbe, watchAttacks } from "./probe.js";
import { rollTable } from "./roller.js";
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

  // The public surface. Macros and, later, the dialog all go through this.
  game.modules.get(MODULE_ID).api = {
    roll: rollTable,
    resetTurn: resetWindow,
    damageTypes,
    categoryFor,
    resolveRoll,
    probe: runProbe
  };

  // Registered here rather than in init so game.socket is definitely connected.
  registerTrigger();

  if (game.settings.get(MODULE_ID, "debugAttacks")) watchAttacks();

  console.log(`${MODULE_ID} | ready — ${tableStatus}`);
});
