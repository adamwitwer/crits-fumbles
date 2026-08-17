import { MODULE_ID } from "./constants.js";
import { damageTypeFor, logMiss } from "./damage-type.js";
import { rollTable } from "./roller.js";
import { consumeWindow } from "./turn-gate.js";

const SOCKET = `module.${MODULE_ID}`;

/**
 * Auto-roll on a natural crit or fumble.
 *
 * dnd5e fires its roll hooks only on the client that made the roll, so a player's
 * attack never reaches the GM's client. Players also cannot write Combat flags, which
 * the turn gate needs. So the rolling client reports the attack and a single GM client
 * decides and posts: that keeps the gate authoritative and produces exactly one card.
 */
export function registerTrigger() {
  Hooks.on("dnd5e.rollAttack", (rolls, data) => {
    if (!game.settings.get(MODULE_ID, "autoTrigger")) return;

    const roll = rolls?.[0];
    const activity = data?.subject;
    const actor = activity?.actor;
    if (!roll || !actor) return;

    const { damageType, seen } = damageTypeFor(activity);
    if (!damageType && (roll.isCritical || roll.isFumble)) logMiss(activity, seen);

    const report = {
      actorUuid: actor.uuid,
      activityName: activity?.name ?? activity?.item?.name ?? null,
      isCritical: !!roll.isCritical,
      isFumble: !!roll.isFumble,
      damageType
    };

    // Handle locally when we are already the acting GM, otherwise hand it over.
    if (isActingGM()) handleAttack(report);
    else game.socket.emit(SOCKET, { action: "attack", report });
  });

  game.socket.on(SOCKET, message => {
    if (message?.action === "attack" && isActingGM()) handleAttack(message.report);
  });
}

/**
 * One client must own this, or every connected GM posts a duplicate card.
 * `activeGM` is Foundry's designated GM; fall back to any GM if it is unavailable.
 */
function isActingGM() {
  const active = game.users?.activeGM;
  if (active) return active.id === game.user.id;
  return game.user.isGM;
}

async function handleAttack({ actorUuid, activityName, isCritical, isFumble, damageType }) {
  const actor = await fromUuid(actorUuid);
  if (!actor) {
    console.warn(`${MODULE_ID} | could not resolve actor ${actorUuid}`);
    return;
  }

  // Runs for every attack, not just crits: the first attack of the turn spends the
  // window whether or not it crits.
  const { eligible, reason } = await consumeWindow(actor);

  // Only a crit or fumble would have produced a card, so only those are worth
  // reporting. Says why nothing happened, which is otherwise invisible.
  const outcome = isCritical ? "critical hit" : isFumble ? "fumble" : null;
  if (outcome) {
    const verdict = !eligible ? `no roll — ${reason}`
      : !damageType ? "no roll — could not determine a damage type (see warning above)"
      : `rolling ${damageType} table — ${reason}`;
    console.log(`${MODULE_ID} | ${actor.name} ${outcome} on "${activityName ?? "attack"}": ${verdict}`);
  }

  if (!eligible) return;
  if (!outcome) return;
  if (!damageType) return; // already logged on the rolling client

  await rollTable({
    kind: isCritical ? "crit" : "fumble",
    damageType,
    actor,
    flavorPrefix: actor.name
  });
}
