import { MODULE_ID } from "./constants.js";
import { runProbe, watchAttacks } from "./probe.js";
import { rollTable } from "./roller.js";
import { categoryFor, damageTypes, loadTables, resolveRoll } from "./tables.js";

Hooks.once("init", () => {
  console.log(`${MODULE_ID} | init`);

  game.settings.register(MODULE_ID, "debugAttacks", {
    name: "Log attack rolls to the console",
    hint: "Diagnostic only. Prints the shape of each attack roll so the auto-trigger can be written against this Foundry/dnd5e version.",
    scope: "world",
    config: true,
    type: Boolean,
    default: true
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
    damageTypes,
    categoryFor,
    resolveRoll,
    probe: runProbe
  };

  if (game.settings.get(MODULE_ID, "debugAttacks")) watchAttacks();

  console.log(`${MODULE_ID} | ready — ${tableStatus}`);
  runProbe();
});
