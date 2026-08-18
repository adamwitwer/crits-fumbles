import { promptForDamageType } from "./apps/damage-prompt.js";
import { checkConditions } from "./conditions.js";
import { registerSceneControl } from "./controls.js";
import { registerAnnouncementListeners } from "./announce.js";
import { MODULE_ID } from "./constants.js";
import { rollTable } from "./roller.js";
import { announceTest, forceCrits, simulate, watchAttacks } from "./testing.js";
import { registerTrigger } from "./trigger.js";
import { categoryFor, damageTypes, loadTables, resolveRoll } from "./tables.js";
import { resetWindow } from "./turn-gate.js";

Hooks.once("init", () => {
  game.settings.register(MODULE_ID, "autoTrigger", {
    name: "CRITSFUMBLES.Settings.AutoTrigger.Name",
    hint: "CRITSFUMBLES.Settings.AutoTrigger.Hint",
    scope: "world",
    config: true,
    type: Boolean,
    default: true
  });

  game.settings.register(MODULE_ID, "promptDamageType", {
    name: "CRITSFUMBLES.Settings.Prompt.Name",
    scope: "world",
    config: true,
    type: String,
    choices: {
      always: "CRITSFUMBLES.Settings.Prompt.Always",
      ambiguous: "CRITSFUMBLES.Settings.Prompt.Ambiguous",
      never: "CRITSFUMBLES.Settings.Prompt.Never"
    },
    default: "always"
  });

  game.settings.register(MODULE_ID, "turnLimit", {
    name: "CRITSFUMBLES.Settings.TurnLimit.Name",
    hint: "CRITSFUMBLES.Settings.TurnLimit.Hint",
    scope: "world",
    config: true,
    type: String,
    choices: {
      first: "CRITSFUMBLES.Settings.TurnLimit.First",
      once: "CRITSFUMBLES.Settings.TurnLimit.Once",
      every: "CRITSFUMBLES.Settings.TurnLimit.Every"
    },
    default: "first"
  });

  game.settings.register(MODULE_ID, "outsideCombat", {
    name: "CRITSFUMBLES.Settings.OutsideCombat.Name",
    hint: "CRITSFUMBLES.Settings.OutsideCombat.Hint",
    scope: "world",
    config: true,
    type: Boolean,
    default: true
  });

  game.settings.register(MODULE_ID, "debugAttacks", {
    name: "CRITSFUMBLES.Settings.Debug.Name",
    hint: "CRITSFUMBLES.Settings.Debug.Hint",
    scope: "world",
    config: true,
    type: Boolean,
    default: false
  });

  // Registered in init so the hook exists before the controls first render.
  registerSceneControl(() => openPrompt());
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
    checkConditions
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
