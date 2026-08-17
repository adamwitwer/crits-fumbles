import { announce } from "./announce.js";
import { MODULE_ID } from "./constants.js";
import { damageTypeFor, logMiss } from "./damage-type.js";
import { rollTable } from "./roller.js";
import { categoryFor } from "./tables.js";
import { evaluateWindow, markWindowSpent } from "./turn-gate.js";

const SOCKET = `module.${MODULE_ID}`;

/**
 * Auto-roll on a natural crit or fumble.
 *
 * Everything happens on the client that rolled the attack: dnd5e fires its roll hooks
 * only there, that is where the player who chose the damage type is sitting, and it
 * means exactly one client posts a card without needing to elect one. The single thing
 * that client may not do is write the Combat flag behind the turn gate, so it asks a
 * GM to record that over the socket.
 */
export function registerTrigger() {
  Hooks.on("dnd5e.rollAttack", (rolls, data) => onAttack(rolls, data).catch(error => {
    console.error(`${MODULE_ID} | attack handling failed`, error);
  }));

  game.socket.on(SOCKET, message => {
    if (message?.action === "markSpent" && isActingGM()) markWindowSpent(message.turnKey);
  });
}

export async function onAttack(rolls, data) {
  if (!game.settings.get(MODULE_ID, "autoTrigger")) return;

  const roll = rolls?.[0];
  const activity = data?.subject;
  const actor = activity?.actor;
  if (!roll || !actor) return;

  // Consulted for every attack, not just crits: the first attack of the turn spends
  // the window whether or not it crits.
  const { eligible, reason, turnKey } = evaluateWindow(actor);
  if (eligible && turnKey) requestSpend(turnKey);

  const outcome = roll.isCritical ? "critical hit" : roll.isFumble ? "fumble" : null;
  if (!outcome) return;

  const name = activity?.name ?? activity?.item?.name ?? "attack";
  const say = verdict => console.log(`${MODULE_ID} | ${actor.name} ${outcome} on "${name}": ${verdict}`);

  if (!eligible) return say(`no roll — ${reason}`);

  const kind = roll.isCritical ? "crit" : "fumble";
  const { known, seen } = damageTypeFor(activity);

  // Fumbles are chosen from three categories, so ambiguity is measured there: an
  // attack that is both bludgeoning and piercing is unambiguously Physical.
  const choices = kind === "fumble"
    ? [...new Set(known.map(categoryFor).filter(Boolean))]
    : known;

  // Ask in chat rather than rolling on a guess: the card stays visible to the table
  // and does not interrupt whoever is mid-turn.
  if (shouldAsk(choices)) {
    say(`announcing in chat — ${reason}`);
    return announce({ actor, kind, detected: known });
  }

  if (!choices.length) {
    logMiss(activity, seen);
    return say("no roll — could not determine a damage type");
  }

  say(`rolling the ${choices[0]} table — ${reason}`);
  await rollTable({ kind, damageType: choices[0], actor, flavorPrefix: actor.name });
}

/**
 * The system often cannot know the damage type — a monk's unarmed strike carries both
 * bludgeoning and force, and the player chooses per strike — so asking is the default.
 */
function shouldAsk(choices) {
  const mode = game.settings.get(MODULE_ID, "promptDamageType");
  if (mode === "never") return false;
  if (mode === "always") return true;
  return choices.length !== 1; // "ambiguous": ask unless exactly one option is certain
}

/** Marking the window spent needs GM rights; do it locally or hand it to a GM. */
function requestSpend(turnKey) {
  if (isActingGM()) markWindowSpent(turnKey);
  else game.socket.emit(SOCKET, { action: "markSpent", turnKey });
}

/** One GM must own the write, or several clients race on the same flag. */
function isActingGM() {
  const active = game.users?.activeGM;
  if (active) return active.id === game.user.id;
  return game.user.isGM;
}
