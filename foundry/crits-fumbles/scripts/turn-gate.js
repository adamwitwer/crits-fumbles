import { MODULE_ID } from "./constants.js";

/**
 * House rule: how often a crit or fumble may roll on a table.
 *
 * Four rulings shape this:
 *  - Whether anything triggers with no encounter running is a separate question, asked
 *    first and in every mode. An out-of-combat attack rolls initiative and starts a
 *    combat, so there is no turn there to limit in the first place.
 *  - Reactions, opportunity attacks and legendary actions happen on someone else's
 *    turn, so under a limit only the creature whose turn it is can ever be eligible.
 *    That is why the state is one flag per turn rather than a set per actor.
 *  - What spends the turn differs by mode, and `spendOn` tells the caller which:
 *    "attack" means the opening attack roll spends it whatever it rolled, "trigger"
 *    means only something that actually fires does.
 *  - With no limit at all, nothing is recorded and every crit and fumble rolls.
 *
 * Split into a read and a write because they need different permissions: any client
 * may read the Combat flag, but only a GM may set it. The rolling client decides, then
 * asks a GM to record the spend.
 */
export function evaluateWindow(actor) {
  const combat = game.combat;

  // Asked before the limit, and whichever limit is set.
  if (!combat?.started) {
    return game.settings.get(MODULE_ID, "outsideCombat")
      ? unlimited("no active combat")
      : blocked("no active combat, and out-of-combat triggering is off");
  }

  const limit = game.settings.get(MODULE_ID, "turnLimit");
  if (limit === "every") return unlimited("no per-turn limit set");

  const current = combat.combatant;
  if (!current) return blocked("combat has no current combatant");

  // Not their turn: a reaction, opportunity attack or legendary action.
  if (!sameActor(current.actor, actor)) {
    return blocked(`not their turn (it is ${current.actor?.name ?? "someone else"}'s) — reaction or legendary action`);
  }

  const turnKey = `${combat.round}:${combat.turn}`;
  const spendOn = limit === "once" ? "trigger" : "attack";
  const spent = combat.getFlag(MODULE_ID, "turn")?.key === turnKey;

  if (spent) {
    return {
      eligible: false,
      reason: spendOn === "trigger"
        ? "something already triggered this turn"
        : "window already spent by an earlier attack this turn",
      turnKey,
      spendOn
    };
  }

  return {
    eligible: true,
    reason: spendOn === "trigger" ? "nothing has triggered yet this turn" : "first attack of their turn",
    turnKey,
    spendOn
  };
}

/** Eligible with nothing to record — no turn is being tracked. */
function unlimited(reason) {
  return { eligible: true, reason, turnKey: null, spendOn: null };
}

function blocked(reason) {
  return { eligible: false, reason, turnKey: null, spendOn: null };
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
