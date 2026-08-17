import { MODULE_ID } from "./constants.js";
import { announce } from "./announce.js";
import { onAttack } from "./trigger.js";

/**
 * Testing helpers.
 *
 * Waiting for a natural 20 is a slow way to exercise this. `simulate` runs the real
 * trigger against a real weapon with a synthetic roll result, and `forceCrits` makes
 * every attack a crit so the genuine dnd5e path can be exercised too.
 */

/**
 * Run the full auto-trigger path — turn rule, damage type prompt, chat card — using a
 * real activity off a real weapon, without waiting for the dice.
 *
 * Only `total`, `isCritical` and `isFumble` are read off the roll, so a plain object
 * stands in for a D20Roll. Everything downstream is the production path.
 */
export async function simulate({ kind = "crit", itemName = null } = {}) {
  const actor = pickActor();
  if (!actor) {
    ui.notifications.warn(`${MODULE_ID}: select a token, or assign yourself a character, first.`);
    return null;
  }

  const activity = findAttackActivity(actor, itemName);
  if (!activity) {
    const what = itemName ? `an attack activity on "${itemName}"` : "any attack activity";
    ui.notifications.warn(`${MODULE_ID}: could not find ${what} on ${actor.name}.`);
    return null;
  }

  const isCritical = kind !== "fumble";
  console.log(`${MODULE_ID} | simulating a ${isCritical ? "critical hit" : "fumble"} for ${actor.name} using "${activity.item?.name ?? activity.name}"`);

  return onAttack(
    [{ total: isCritical ? 20 : 1, isCritical, isFumble: !isCritical }],
    { subject: activity }
  );
}

/**
 * Lower the actor's crit threshold to 1 so every weapon attack crits.
 *
 * This is the dnd5e flag that class features like Improved Critical use. Exercises the
 * real dnd5e.rollAttack path rather than a stand-in, at the cost of touching the actor.
 */
export async function forceCrits(enabled = true) {
  const actor = pickActor();
  if (!actor) {
    ui.notifications.warn(`${MODULE_ID}: select a token, or assign yourself a character, first.`);
    return null;
  }

  if (enabled) {
    await actor.setFlag("dnd5e", "weaponCriticalThreshold", 1);
  } else {
    await actor.unsetFlag("dnd5e", "weaponCriticalThreshold");
  }

  // Report what actually stuck: the flag path is dnd5e's, not ours, and could move.
  const now = actor.getFlag("dnd5e", "weaponCriticalThreshold");
  const state = enabled
    ? (now === 1 ? "every weapon attack will now crit" : `flag did not apply (reads back as ${now})`)
    : (now === undefined ? "restored to normal" : `flag did not clear (reads back as ${now})`);
  const message = `${MODULE_ID}: ${actor.name} — ${state}`;

  console.log(message);
  ui.notifications.info(message);
  return now;
}

/** Post an announcement card directly, without an attack or the turn rule. */
export async function announceTest({ kind = "crit", detected = [] } = {}) {
  return announce({ actor: pickActor(), kind, detected });
}

function pickActor() {
  return canvas?.tokens?.controlled?.[0]?.actor ?? game.user?.character ?? null;
}

/** Activities live on items; shapes have moved between dnd5e versions, so be lenient. */
function findAttackActivity(actor, itemName) {
  for (const item of actor.items ?? []) {
    if (itemName && item.name !== itemName) continue;

    const activities = item.system?.activities;
    if (!activities) continue;

    const list = activities.contents ?? (typeof activities[Symbol.iterator] === "function"
      ? Array.from(activities)
      : Object.values(activities));

    const attack = list.find(activity => activity?.type === "attack");
    if (attack) return attack;
  }
  return null;
}
