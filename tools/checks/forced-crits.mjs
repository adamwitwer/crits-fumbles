import { captureConsole, load, reporter, stubFoundry } from "./harness.mjs";

export const name = "the forced-crit sweep";

/**
 * `forceCrits` writes a real dnd5e flag to a real character sheet, and a Champion
 * Fighter's Improved Critical writes to the same one. The sweep that undoes our
 * testing must never touch theirs, so the classification is checked here rather than
 * discovered on someone's sheet.
 */

/** A stand-in document. `stored` is what the sweep reads; `live` is what reads back. */
function doc(name, stored, { canModify = true, sticky = false } = {}) {
  const flags = stored === undefined ? {} : { dnd5e: { weaponCriticalThreshold: stored } };
  const self = {
    name,
    _source: { flags },
    _live: stored,
    canUserModify: () => canModify,
    getFlag: () => self._live,
    // `sticky` models an Active Effect supplying the value: unsetting the stored flag
    // does not remove it, and the sweep must not claim otherwise.
    unsetFlag: async () => { if (!sticky) self._live = undefined; }
  };
  return self;
}

function token(name, stored, { actorLink = false } = {}) {
  return {
    name,
    actorLink,
    delta: { _source: { flags: stored === undefined ? {} : { dnd5e: { weaponCriticalThreshold: stored } } } },
    actor: doc(name, stored)
  };
}

export default async function run() {
  await stubFoundry();
  const r = reporter();

  globalThis.game.settings = { get: () => false };
  globalThis.game.user = { isGM: true };
  globalThis.ui = { notifications: { info: () => {}, warn: () => {} } };
  const table = console.table;
  console.table = () => {};

  const { clearForcedCrits } = await load("testing.js", "sweep");

  // The sweep narrates itself to the console; keep that out of the suite's own output.
  const sweep = async options => {
    let rows;
    await captureConsole(async () => { rows = await clearForcedCrits(options); });
    return rows;
  };

  const world = ({ actors = [], scenes = [] }) => {
    globalThis.game.actors = actors;
    globalThis.game.scenes = scenes;
  };
  const find = (rows, name) => rows.find(row => row.name === name);

  // --- what it touches, and what it must not ---
  const champion = doc("Champion", 19);
  const forced = doc("Rahib", 1);
  world({ actors: [forced, champion, doc("Untouched", undefined)] });

  let rows = await sweep();
  r.equal(rows.length, 2, "only actors carrying a threshold are reported");
  r.equal(find(rows, "Rahib").result, "cleared", "a forced threshold of 1 is cleared");
  r.equal(forced._live, undefined, "the flag is actually gone afterwards");
  r.check(find(rows, "Champion").result.startsWith("left alone"),
    "a Champion's 19 is left alone — Improved Critical is not ours to clear",
    find(rows, "Champion").result);
  r.equal(champion._live, 19, "and its value is untouched");

  // --- dry run ---
  const peek = doc("Rahib", 1);
  world({ actors: [peek] });
  rows = await sweep({ dryRun: true });
  r.equal(rows[0].result, "would clear", "a dry run says what it would do");
  r.equal(peek._live, 1, "and changes nothing");

  // --- unlinked tokens keep their own overrides ---
  world({
    actors: [],
    scenes: [{ name: "Cave", tokens: [token("Goblin", 1), token("Goblin Boss", undefined), token("Linked", 1, { actorLink: true })] }]
  });
  rows = await sweep();
  r.equal(rows.length, 1, "an unlinked token carrying the flag in its delta is found");
  r.equal(rows[0].where, "Token — Cave", "and is labelled with its scene");
  r.check(!find(rows, "Linked"), "a linked token is left to its base actor, not reported twice");

  // --- honest about what it could not do ---
  world({ actors: [doc("Someone Else's", 1, { canModify: false })] });
  rows = await sweep();
  r.check(rows[0].result.startsWith("skipped — no permission"),
    "a document the user cannot update is skipped, not failed", rows[0].result);

  world({ actors: [doc("Effect-driven", 1, { sticky: true })] });
  rows = await sweep();
  r.check(rows[0].result.includes("Active Effect"),
    "a value that survives the unset is reported, not claimed as cleared", rows[0].result);

  // --- nothing to do ---
  world({ actors: [doc("Clean", undefined)] });
  rows = await sweep();
  r.equal(rows.length, 0, "a clean world reports nothing");

  console.table = table;
  return r.failures;
}
