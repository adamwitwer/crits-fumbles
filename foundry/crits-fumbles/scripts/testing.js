import { MODULE_ID } from "./constants.js";
import { announce } from "./announce.js";
import { onAttack } from "./trigger.js";
import { evaluateWindow } from "./turn-gate.js";

/**
 * Testing helpers.
 *
 * Waiting for a natural 20 is a slow way to exercise this. `simulate` runs the real
 * trigger against a real weapon with a synthetic roll result, and `forceCrits` makes
 * every attack a crit so the genuine dnd5e path can be exercised too.
 */

/**
 * dnd5e's crit threshold flag, and the value `forceCrits` writes.
 *
 * A Champion Fighter stores 19 or 18 here for Improved Critical, so the flag itself is
 * not ours to clear — only the value 1, which no real feature produces.
 */
const CRIT_SCOPE = "dnd5e";
const CRIT_KEY = "weaponCriticalThreshold";
const FORCED = 1;

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
    await actor.setFlag(CRIT_SCOPE, CRIT_KEY, FORCED);
  } else {
    await actor.unsetFlag(CRIT_SCOPE, CRIT_KEY);
  }

  // Report what actually stuck: the flag path is dnd5e's, not ours, and could move.
  const now = actor.getFlag(CRIT_SCOPE, CRIT_KEY);
  const state = enabled
    ? (now === FORCED ? "every weapon attack will now crit" : `flag did not apply (reads back as ${now})`)
    : (now === undefined ? "restored to normal" : `flag did not clear (reads back as ${now})`);
  const message = `${MODULE_ID}: ${actor.name} — ${state}`;

  console.log(message);

  // This writes to the character in the world database, not to this browser. Said
  // plainly and left on screen, because a test flag that outlives the session reads
  // as a module bug days later, on another machine, to whoever finds it.
  if (enabled) {
    ui.notifications.warn(
      `${message}. Saved to the sheet in this world — it survives a refresh and follows ` +
      `the character to any browser. Undo with CritsFumbles.forceCrits(false), or ` +
      `CritsFumbles.clearForcedCrits() to sweep every actor.`,
      { permanent: true }
    );
  } else {
    ui.notifications.info(message);
  }
  return now;
}

/**
 * Find every actor left with a forced crit threshold, and clear it.
 *
 * `forceCrits` writes to the actor document, which lives in the world database on the
 * server — so it outlasts the session, the browser and the machine. This is the way
 * back when you no longer remember which character you used for testing.
 *
 * Reports what it leaves alone as well as what it clears: a Champion's Improved
 * Critical uses the same flag, and a sweep that stripped it would break a real sheet.
 */
export async function clearForcedCrits({ dryRun = false } = {}) {
  const carriers = [];

  // `_source` is what is stored on the document. The computed `flags` could carry a
  // value from an Active Effect instead, which unsetting the flag would not remove.
  for (const actor of game.actors ?? []) {
    const value = actor._source?.flags?.[CRIT_SCOPE]?.[CRIT_KEY];
    if (value !== undefined) carriers.push({ where: "Actor", name: actor.name, value, doc: actor });
  }

  // An unlinked token keeps its own overrides in the delta, separate from the base
  // actor — so a forced flag can hide on one goblin and nowhere else.
  for (const scene of game.scenes ?? []) {
    for (const token of scene.tokens ?? []) {
      if (token.actorLink) continue;
      const value = token.delta?._source?.flags?.[CRIT_SCOPE]?.[CRIT_KEY];
      if (value !== undefined) {
        carriers.push({ where: `Token — ${scene.name}`, name: token.name, value, doc: token.actor });
      }
    }
  }

  for (const entry of carriers) {
    if (entry.value !== FORCED) {
      entry.result = "left alone — a real crit threshold";
    } else if (dryRun) {
      entry.result = "would clear";
    } else if (!entry.doc?.canUserModify?.(game.user, "update")) {
      entry.result = "skipped — no permission, ask a GM";
    } else {
      try {
        await entry.doc.unsetFlag(CRIT_SCOPE, CRIT_KEY);
        const now = entry.doc.getFlag(CRIT_SCOPE, CRIT_KEY);
        entry.result = now === undefined ? "cleared" : `still reads ${now} — look for an Active Effect`;
      } catch (error) {
        entry.result = `failed — ${error.message}`;
      }
    }
  }

  const rows = carriers.map(({ where, name, value, result }) => ({ where, name, threshold: value, result }));
  const forced = carriers.filter(entry => entry.value === FORCED).length;
  const cleared = carriers.filter(entry => entry.result === "cleared").length;

  let message;
  if (!carriers.length) message = `${MODULE_ID}: nothing carries a weapon crit threshold. Nothing to clear.`;
  else if (dryRun) message = `${MODULE_ID}: ${forced} forced of ${carriers.length} carrying a threshold. Nothing changed — dry run.`;
  else message = `${MODULE_ID}: cleared ${cleared} of ${forced} forced (${carriers.length} carrying a threshold in all).`;

  console.log(message);
  if (rows.length) console.table(rows);
  ui.notifications.info(message);
  return rows;
}

/**
 * Print the turn rule's live verdict for the selected token.
 *
 * The gate already explains itself — every decision carries a reason — but that
 * explanation is only logged when a real crit is turned away. Walking an encounter is
 * far easier when you can ask before the dice whether this creature is eligible.
 */
export function turnStatus() {
  const actor = pickActor();
  if (!actor) {
    ui.notifications.warn(`${MODULE_ID}: select a token, or assign yourself a character, first.`);
    return null;
  }

  const combat = game.combat;
  const state = evaluateWindow(actor);
  const settings = {
    autoTrigger: game.settings.get(MODULE_ID, "autoTrigger"),
    turnLimit: game.settings.get(MODULE_ID, "turnLimit"),
    outsideCombat: game.settings.get(MODULE_ID, "outsideCombat")
  };
  const spentKey = combat?.started ? (combat.getFlag(MODULE_ID, "turn")?.key ?? null) : null;

  console.group(`${MODULE_ID} | turn status for ${actor.name}`);
  console.log(combat?.started
    ? `combat: round ${combat.round}, turn ${combat.turn} — currently ${combat.combatant?.actor?.name ?? "nobody"}`
    : "combat: none running");
  console.log(`settings: limit=${settings.turnLimit}, outsideCombat=${settings.outsideCombat}, autoTrigger=${settings.autoTrigger}`);
  console.log(`this turn's window: ${spentKey ? `spent (${spentKey})` : "unspent"}`);
  console.log(
    `%c${state.eligible ? "ELIGIBLE" : "NOT ELIGIBLE"}%c — ${state.reason}`,
    `font-weight:bold;color:${state.eligible ? "#2e7d32" : "#c62828"}`,
    ""
  );
  if (state.eligible && state.spendOn) {
    console.log(`spends the turn on: ${state.spendOn === "attack" ? "the attack roll itself, whatever it rolls" : "a crit or fumble actually firing"}`);
  }
  if (!settings.autoTrigger) {
    console.log("note: automatic rolling is off, so the dice trigger nothing regardless of the above.");
  }
  console.groupEnd();

  return { actor: actor.name, ...state, ...settings, spentKey };
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

/**
 * Passive listener: logs the shape of an attack roll without acting on it.
 *
 * Turn on "Log attack rolls to the console" and make one attack: the console shows
 * the roll's crit flags and the activity's damage shape, which is where the answer
 * lives whenever an attack does not trigger what you expected.
 */
export function watchAttacks() {
  Hooks.on("dnd5e.rollAttack", (rolls, data) => {
    const roll = rolls?.[0];
    const activity = data?.subject;

    console.group(`${MODULE_ID} | dnd5e.rollAttack observed`);
    console.log("roll.total:", roll?.total, "| isCritical:", roll?.isCritical, "| isFumble:", roll?.isFumble);
    console.log("activity type:", activity?.type, "| name:", activity?.name);
    console.log("activity.damage:", activity?.damage);
    console.log("activity.item?.system?.damage:", activity?.item?.system?.damage);
    console.log("actor:", activity?.actor?.name, "| id:", activity?.actor?.id);
    console.log("full activity (expand to explore):", activity);
    console.groupEnd();
  });
}
