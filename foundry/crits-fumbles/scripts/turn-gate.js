import { MODULE_ID } from "./constants.js";

/**
 * House rule: only a combatant's first attack of their own turn can roll on a table.
 *
 * Three rulings shape this:
 *  - Reactions, opportunity attacks and legendary actions never trigger, so only the
 *    creature whose turn it is can ever be eligible. That means the state is one flag
 *    per turn rather than a per-actor set.
 *  - The window is spent by the first attack roll whether or not it crits, so this is
 *    consulted on every attack, before the crit check.
 *  - Outside combat there are no turns to track, so everything is eligible.
 *
 * Split into a read and a write because they need different permissions: any client
 * may read the Combat flag, but only a GM may set it. The rolling client decides, then
 * asks a GM to record the spend.
 */
export function evaluateWindow(actor) {
  if (!game.settings.get(MODULE_ID, "firstAttackOnly")) {
    return { eligible: true, reason: "first-attack rule is off", turnKey: null };
  }

  const combat = game.combat;

  if (!combat?.started) {
    return game.settings.get(MODULE_ID, "outsideCombat")
      ? { eligible: true, reason: "no active combat", turnKey: null }
      : { eligible: false, reason: "no active combat, and out-of-combat triggering is off", turnKey: null };
  }

  const current = combat.combatant;
  if (!current) return { eligible: false, reason: "combat has no current combatant", turnKey: null };

  // Not their turn: a reaction, opportunity attack or legendary action.
  if (!sameActor(current.actor, actor)) {
    return {
      eligible: false,
      reason: `not their turn (it is ${current.actor?.name ?? "someone else"}'s) — reaction or legendary action`,
      turnKey: null
    };
  }

  const turnKey = `${combat.round}:${combat.turn}`;
  const state = combat.getFlag(MODULE_ID, "turn");
  if (state?.key === turnKey) {
    return { eligible: false, reason: "window already spent by an earlier attack this turn", turnKey };
  }

  return { eligible: true, reason: "first attack of their turn", turnKey };
}

/** Record that this turn's window is spent. GM only. */
export async function markWindowSpent(turnKey) {
  const combat = game.combat;
  if (!combat?.started || !turnKey) return;
  await combat.setFlag(MODULE_ID, "turn", { key: turnKey });
}

/** Clear the current turn's window so it can be rolled again. GM only. */
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
