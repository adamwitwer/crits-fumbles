import { load, reporter, stubFoundry } from "./harness.mjs";

export const name = "the first-attack turn rule";

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

  const settings = { firstAttackOnly: true, outsideCombat: true };
  globalThis.game.settings = { get: (_, key) => settings[key] };

  const gate = await load("turn-gate.js", "gate");
  const evaluate = (a, c) => { globalThis.game.combat = c; return gate.evaluateWindow(a); };

  const hero = actor("hero");

  // The ordinary case.
  let result = evaluate(hero, combat({ current: hero }));
  r.check(result.eligible && result.turnKey === "1:0", "the first attack of a turn is eligible", JSON.stringify(result));

  // Spent by the first attack whether or not it crit — the house rule's sharp edge.
  result = evaluate(hero, combat({ current: hero, flag: { key: "1:0" } }));
  r.check(!result.eligible && /already spent/.test(result.reason), "a second attack in the same turn is not eligible", result.reason);

  // A new turn reopens it.
  result = evaluate(hero, combat({ current: hero, turn: 1, flag: { key: "1:0" } }));
  r.check(result.eligible && result.turnKey === "1:1", "the next turn opens a fresh window", JSON.stringify(result));
  result = evaluate(hero, combat({ current: hero, round: 2, flag: { key: "1:0" } }));
  r.check(result.eligible && result.turnKey === "2:0", "the next round opens a fresh window", JSON.stringify(result));

  // Reactions and legendary actions happen on someone else's turn.
  result = evaluate(hero, combat({ current: actor("villain") }));
  r.check(!result.eligible && /not their turn/.test(result.reason), "an attack on another creature's turn is not eligible", result.reason);
  r.equal(result.turnKey, null, "an ineligible attack claims no turn key");

  // Unlinked token actors can share an id, so uuid decides when both have one.
  const tokenA = actor("npc", "Scene.x.Token.a.Actor.npc");
  const tokenB = actor("npc", "Scene.x.Token.b.Actor.npc");
  r.check(!evaluate(tokenA, combat({ current: tokenB })).eligible,
    "two unlinked tokens sharing an id are told apart by uuid");
  r.check(evaluate(tokenA, combat({ current: tokenA })).eligible,
    "the same token actor still matches itself");

  // Combat states.
  r.check(evaluate(hero, combat({ started: false })).eligible, "outside combat everything is eligible");
  r.check(evaluate(hero, null).eligible, "with no combat at all everything is eligible");
  r.check(!evaluate(hero, combat({ current: null })).eligible, "a combat with no current combatant is not eligible");

  settings.outsideCombat = false;
  r.check(!evaluate(hero, combat({ started: false })).eligible,
    "with out-of-combat triggering off, no combat means no roll");
  settings.outsideCombat = true;

  // The whole rule can be switched off.
  settings.firstAttackOnly = false;
  result = evaluate(hero, combat({ current: hero, flag: { key: "1:0" } }));
  r.check(result.eligible && result.turnKey === null,
    "with the rule off, a spent window is still eligible and claims no key", JSON.stringify(result));
  settings.firstAttackOnly = true;

  // The write half.
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
