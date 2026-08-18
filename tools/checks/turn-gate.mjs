import { load, reporter, stubFoundry } from "./harness.mjs";

export const name = "the per-turn limit";

const actor = (id, uuid = null) => ({ id, name: id, ...(uuid ? { uuid } : {}) });

/** A combat whose flag store is a plain object, so a spend can be observed. */
function combat({ started = true, round = 1, turn = 0, current = actor("hero"), flag = null } = {}) {
  const store = { turn: flag };
  return {
    started, round, turn,
    combatant: current ? { actor: current } : null,
    getFlag: (_, key) => store[key],
    setFlag: async (_, key, value) => { store[key] = value; },
    unsetFlag: async (_, key) => { delete store[key]; },
    _store: store
  };
}

export default async function run() {
  await stubFoundry();
  const r = reporter();

  const settings = { turnLimit: "first", outsideCombat: true };
  globalThis.game.settings = { get: (_, key) => settings[key] };

  const gate = await load("turn-gate.js", "gate");
  const evaluate = (a, c) => { globalThis.game.combat = c; return gate.evaluateWindow(a); };

  const hero = actor("hero");
  const villain = actor("villain");

  // --- "Only on the turn's first attack roll" ---
  settings.turnLimit = "first";
  let result = evaluate(hero, combat({ current: hero }));
  r.check(result.eligible && result.turnKey === "1:0" && result.spendOn === "attack",
    "first: the opening attack is eligible and spends the turn on the attack", JSON.stringify(result));
  r.check(!evaluate(hero, combat({ current: hero, flag: { key: "1:0" } })).eligible,
    "first: a later attack in the same turn is not eligible");
  r.check(evaluate(hero, combat({ current: hero, turn: 1, flag: { key: "1:0" } })).eligible,
    "first: the next turn opens a fresh window");
  r.check(evaluate(hero, combat({ current: hero, round: 2, flag: { key: "1:0" } })).eligible,
    "first: the next round opens a fresh window");

  // --- "Once each turn, on any attack" ---
  settings.turnLimit = "once";
  result = evaluate(hero, combat({ current: hero }));
  r.check(result.eligible && result.turnKey === "1:0" && result.spendOn === "trigger",
    "once: eligible, and the turn is spent by what triggers rather than by the attack", JSON.stringify(result));
  result = evaluate(hero, combat({ current: hero, flag: { key: "1:0" } }));
  r.check(!result.eligible && /already triggered/.test(result.reason),
    "once: nothing more triggers after something has", result.reason);

  // --- "Every crit and fumble" ---
  settings.turnLimit = "every";
  result = evaluate(hero, combat({ current: hero, flag: { key: "1:0" } }));
  r.check(result.eligible && result.turnKey === null && result.spendOn === null,
    "every: eligible regardless, and nothing is recorded", JSON.stringify(result));
  r.check(evaluate(hero, combat({ current: villain })).eligible,
    "every: reactions and legendary actions fire too");

  // --- Reactions, under either limit ---
  for (const limit of ["first", "once"]) {
    settings.turnLimit = limit;
    const other = evaluate(hero, combat({ current: villain }));
    r.check(!other.eligible && /not their turn/.test(other.reason),
      `${limit}: an attack on another creature's turn is not eligible`, other.reason);
    r.equal(other.turnKey, null, `${limit}: an ineligible attack claims no turn key`);
  }

  // Unlinked token actors can share an id, so uuid decides when both have one.
  settings.turnLimit = "first";
  const tokenA = actor("npc", "Scene.x.Token.a.Actor.npc");
  const tokenB = actor("npc", "Scene.x.Token.b.Actor.npc");
  r.check(!evaluate(tokenA, combat({ current: tokenB })).eligible,
    "two unlinked tokens sharing an id are told apart by uuid");
  r.check(evaluate(tokenA, combat({ current: tokenA })).eligible,
    "the same token actor still matches itself");
  r.check(!evaluate(hero, combat({ current: null })).eligible,
    "a combat with no current combatant is not eligible");

  // --- Out of combat: independent of the limit, and asked first ---
  for (const limit of ["first", "once", "every"]) {
    settings.turnLimit = limit;

    settings.outsideCombat = true;
    r.check(evaluate(hero, combat({ started: false })).eligible,
      `${limit}: out-of-combat triggering on means a crit with no encounter rolls`);
    r.check(evaluate(hero, null).eligible, `${limit}: no combat object at all is still eligible`);

    settings.outsideCombat = false;
    const off = evaluate(hero, combat({ started: false }));
    r.check(!off.eligible && /out-of-combat triggering is off/.test(off.reason),
      `${limit}: out-of-combat triggering off blocks it, whatever the limit`, off.reason);
  }
  settings.outsideCombat = true;

  // --- The write half ---
  settings.turnLimit = "first";
  const live = combat({ current: hero });
  globalThis.game.combat = live;
  await gate.markWindowSpent("1:0");
  r.check(live._store.turn?.key === "1:0", "marking a spend records the turn key", JSON.stringify(live._store));
  r.check(!gate.evaluateWindow(hero).eligible, "the recorded spend closes the window");
  await gate.resetWindow();
  r.check(gate.evaluateWindow(hero).eligible, "resetTurn reopens it");

  await gate.markWindowSpent(null);
  r.check(live._store.turn === undefined, "a null turn key records nothing");
  globalThis.game.combat = null;
  r.equal(await gate.resetWindow(), false, "resetting with no combat reports that it did nothing");

  return r.failures;
}
