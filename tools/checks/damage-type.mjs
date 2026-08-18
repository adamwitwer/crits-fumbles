import { load, reporter, stubFoundry } from "./harness.mjs";

export const name = "damage type detection";

/** Shorthand for the dnd5e 5.x activity shape. */
const activity = ({ parts = [], base = null, legacy = null, includeBase = undefined, name = "Weapon" }) => ({
  damage: { parts, ...(includeBase === undefined ? {} : { includeBase }) },
  item: { name, system: { damage: { ...(base ? { base } : {}), ...(legacy ? { parts: legacy } : {}) } } }
});

export default async function run() {
  await stubFoundry();
  const r = reporter();
  const { damageTypeFor } = await load("damage-type.js");
  await (await load("tables.js")).loadTables();

  const first = a => damageTypeFor(a).damageType;

  // The real bug, found from a console dump of an actual attack: includeBase means the
  // weapon's base damage is the attack's primary type and the activity's parts are
  // riders on top. Getting this backwards rolls fire for a flame tongue's slash.
  r.equal(first(activity({
    name: "Flame Tongue Longsword",
    includeBase: true,
    base: { types: new Set(["slashing"]) },
    parts: [{ types: new Set(["fire"]) }]
  })), "slashing", "includeBase: the weapon's base type leads, riders follow");

  r.equal(first(activity({
    name: "Fire Bolt",
    includeBase: false,
    parts: [{ types: new Set(["fire"]) }],
    base: { types: new Set(["bludgeoning"]) }
  })), "fire", "without includeBase the activity's own parts lead");

  // A monk's unarmed strike: two types, player picks per strike. Both must survive to
  // the prompt rather than one being silently chosen.
  const monk = damageTypeFor(activity({
    name: "Unarmed Strike", includeBase: true, base: { types: new Set(["bludgeoning", "force"]) }
  }));
  r.check(monk.known.length === 2 && monk.known.includes("bludgeoning") && monk.known.includes("force"),
    "a two-type strike reports both, so the player is asked",
    JSON.stringify(monk.known));

  // Shapes that have all appeared across dnd5e versions.
  r.equal(first(activity({ parts: [{ type: "cold" }] })), "cold", "a part with a single `type` string");
  r.equal(first(activity({ parts: [{ types: ["acid"] }] })), "acid", "a part with `types` as an array");
  r.equal(first(activity({ base: { type: "piercing" } })), "piercing", "base damage as a single `type`");
  r.equal(first(activity({ legacy: [["1d8", "necrotic"]] })), "necrotic", "the dnd5e 3.x [[formula, type]] shape");
  r.equal(first(activity({ parts: [{ types: new Set(["PIERCING"]) }] })), "piercing", "types are matched case-insensitively");

  // Nothing usable must be reported as nothing, not guessed.
  r.equal(first(activity({})), null, "an activity with no damage yields no type");
  r.equal(first(activity({ parts: [{ types: new Set(["chaos"]) }] })), null, "a type with no table is not used");
  r.equal(damageTypeFor(null).damageType, null, "a missing activity does not throw");
  r.equal(damageTypeFor(undefined).known.length, 0, "an undefined activity yields no types");

  // `seen` exists to diagnose a miss; it keeps what the tables reject.
  const odd = damageTypeFor(activity({ parts: [{ types: new Set(["chaos"]) }] }));
  r.check(odd.seen.includes("chaos"), "an unrecognised type is still reported in `seen`", JSON.stringify(odd.seen));

  // Duplicates across base and parts must not produce a repeated prompt option.
  const dup = damageTypeFor(activity({
    includeBase: true, base: { types: new Set(["slashing"]) }, parts: [{ types: new Set(["slashing"]) }]
  }));
  r.equal(dup.known.length, 1, "a type listed on both base and parts appears once");

  return r.failures;
}
