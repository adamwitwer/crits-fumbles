import { load, reporter, stubFoundry } from "./harness.mjs";

export const name = "what triggers, and what spends the turn";

/**
 * A world with one combat, driven attack by attack.
 *
 * This is where the per-turn limits actually differ: the gate only reports *when* the
 * turn is spent, and the trigger is what acts on it. A limit that reads correctly and
 * spends at the wrong moment would pass every gate check and still be wrong at the
 * table.
 */
function world({ limit = "first", outsideCombat = true, prompt = "never", inCombat = true } = {}) {
  const hero = { id: "hero", name: "Rahib", uuid: "Actor.hero" };
  const flags = {};
  const posted = [];

  const combat = {
    started: inCombat, round: 1, turn: 0,
    combatant: { actor: hero },
    getFlag: (_, key) => flags[key],
    setFlag: async (_, key, value) => { flags[key] = value; },
    unsetFlag: async (_, key) => { delete flags[key]; }
  };

  Object.assign(globalThis.game, {
    combat: inCombat ? combat : null,
    settings: { get: (_, key) => ({ autoTrigger: true, promptDamageType: prompt, turnLimit: limit, outsideCombat })[key] },
    user: { id: "gm", isGM: true },
    users: { activeGM: { id: "gm" } },
    socket: { on: () => {}, emit: () => {} }
  });

  globalThis.ChatMessage = {
    getSpeaker: () => ({}),
    create: async message => { posted.push(message); return message; }
  };
  globalThis.Roll = class {
    constructor() { this.total = 42; }
    async evaluate() { return this; }
  };

  // A longsword: one unambiguous damage type, so nothing prompts and every eligible
  // crit rolls straight through to a card.
  const activity = {
    actor: hero, name: "Longsword", type: "attack",
    damage: { includeBase: true, parts: [] },
    item: { name: "Longsword", system: { damage: { base: { types: new Set(["slashing"]) } } } }
  };

  return {
    hero, combat, posted, activity,
    spent: () => flags.turn?.key ?? null,
    nextTurn: () => { combat.turn += 1; }
  };
}

export default async function run() {
  await stubFoundry();
  const r = reporter();
  await (await load("tables.js")).loadTables();

  // The trigger narrates every decision it declines to act on. The assertions below
  // already say what was expected, so keep the run readable.
  const chatter = console.log;
  const quiet = fn => async (...args) => { console.log = () => {}; try { return await fn(...args); } finally { console.log = chatter; } };

  const roll = (kind = null) => [{
    total: kind === "crit" ? 20 : kind === "fumble" ? 1 : 13,
    isCritical: kind === "crit",
    isFumble: kind === "fumble"
  }];

  // --- "Only on the turn's first attack roll" ---
  {
    const w = world({ limit: "first" });
    const { onAttack: raw } = await load("trigger.js", "first");
    const onAttack = quiet(raw);

    await onAttack(roll(), { subject: w.activity });          // ordinary opening swing
    r.equal(w.spent(), "1:0", "first: an ordinary opening attack spends the turn");
    r.equal(w.posted.length, 0, "first: ...and posts nothing, having not crit");

    await onAttack(roll("crit"), { subject: w.activity });    // the crit your question was about
    r.equal(w.posted.length, 0, "first: a crit on the second attack does not fire");

    w.nextTurn();
    await onAttack(roll("crit"), { subject: w.activity });
    r.equal(w.posted.length, 1, "first: a crit opening the next turn does fire");
  }

  // --- "Once each turn, on any attack" ---
  {
    const w = world({ limit: "once" });
    const { onAttack: raw } = await load("trigger.js", "once");
    const onAttack = quiet(raw);

    await onAttack(roll(), { subject: w.activity });
    r.equal(w.spent(), null, "once: an ordinary attack leaves the turn open");
    r.equal(w.posted.length, 0, "once: ...and posts nothing");

    await onAttack(roll("crit"), { subject: w.activity });
    r.equal(w.posted.length, 1, "once: a crit on the second attack fires");
    r.equal(w.spent(), "1:0", "once: ...and that is what spends the turn");

    await onAttack(roll("fumble"), { subject: w.activity });
    r.equal(w.posted.length, 1, "once: nothing more fires this turn");

    w.nextTurn();
    await onAttack(roll("fumble"), { subject: w.activity });
    r.equal(w.posted.length, 2, "once: the next turn fires again");
  }

  // --- "Every crit and fumble" ---
  {
    const w = world({ limit: "every" });
    const { onAttack: raw } = await load("trigger.js", "every");
    const onAttack = quiet(raw);

    for (const kind of ["crit", "crit", "fumble"]) await onAttack(roll(kind), { subject: w.activity });
    r.equal(w.posted.length, 3, "every: three crits and fumbles in one turn all fire");
    r.equal(w.spent(), null, "every: nothing is recorded on the combat");
  }

  // --- Out of combat, independent of the limit ---
  for (const limit of ["first", "once", "every"]) {
    const on = world({ limit, inCombat: false, outsideCombat: true });
    let trigger = await load("trigger.js", `ooc-on-${limit}`);
    await quiet(trigger.onAttack)(roll("crit"), { subject: on.activity });
    r.equal(on.posted.length, 1, `${limit}: out of combat with triggering on, a crit fires`);

    const off = world({ limit, inCombat: false, outsideCombat: false });
    trigger = await load("trigger.js", `ooc-off-${limit}`);
    await quiet(trigger.onAttack)(roll("crit"), { subject: off.activity });
    r.equal(off.posted.length, 0, `${limit}: out of combat with triggering off, it does not`);
  }

  // A crit whose damage type cannot be worked out must not quietly eat the turn.
  {
    const w = world({ limit: "once" });
    const { onAttack: raw } = await load("trigger.js", "unknown");
    const onAttack = quiet(raw);
    const mystery = { ...w.activity, item: { name: "Odd", system: { damage: { base: { types: new Set(["chaos"]) } } } } };
    const original = console.warn;
    console.warn = () => {};
    await onAttack(roll("crit"), { subject: mystery });
    console.warn = original;
    r.equal(w.posted.length, 0, "an unresolvable damage type posts nothing");
    r.equal(w.spent(), null, "once: ...and leaves the turn open for a later attack");
  }

  for (const key of ["ChatMessage", "Roll"]) delete globalThis[key];
  return r.failures;
}
