import { MODULE_ID } from "./constants.js";

/**
 * House rule: only a combatant's first attack of their own turn can roll on a table.
 *
 * Three rulings shape this:
 *  - Reactions, opportunity attacks and legendary actions never trigger, so only the
 *    creature whose turn it is can ever be eligible. That means the state is one flag
 *    per turn rather than a per-actor set.
 *  - The window is spent by the first attack roll whether or not it crits, so this is
 *    called on every attack, before the crit check.
 *  - Outside combat there are no turns to track, so everything is eligible.
 *
 * State lives on the Combat document so it survives a reload, and encodes the turn it
 * belongs to so a new turn invalidates it without needing an updateCombat listener.
 */
export async function consumeWindow(actor) {
  const combat = game.combat;

  if (!combat?.started) {
    return game.settings.get(MODULE_ID, "outsideCombat");
  }

  const current = combat.combatant;
  if (!current) return false;

  // Not their turn: a reaction, opportunity attack or legendary action.
  if (!sameActor(current.actor, actor)) return false;

  const turnKey = `${combat.round}:${combat.turn}`;
  const state = combat.getFlag(MODULE_ID, "turn");
  if (state?.key === turnKey) return false; // already spent this turn

  await combat.setFlag(MODULE_ID, "turn", { key: turnKey });
  return true;
}

/** Clear the current turn's window so it can be rolled again. */
export async function resetWindow() {
  const combat = game.combat;
  if (!combat?.started) return false;
  await combat.unsetFlag(MODULE_ID, "turn");
  return true;
}

function sameActor(a, b) {
  if (!a || !b) return false;
  // uuid distinguishes unlinked token actors that can share an id.
  if (a.uuid && b.uuid) return a.uuid === b.uuid;
  return a.id === b.id;
}
