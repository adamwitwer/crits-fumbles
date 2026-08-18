import { load, reporter, stubFoundry } from "./harness.mjs";

export const name = "tables and labels";

export default async function run() {
  const { tables } = await stubFoundry();
  const r = reporter();
  const t = await load("tables.js");
  await t.loadTables();

  // The bug this guards: the same three buckets were labelled "Magic" as a crit
  // picker group header and "Magical" in the fumble list.
  const groups = t.damageTypeGroups().map(g => g.label);
  const categories = t.fumbleCategories().map(c => c.label);
  r.check(JSON.stringify(groups) === JSON.stringify(categories),
    `crit groups and fumble list use one set of names: ${groups.join(" / ")}`,
    `groups ${JSON.stringify(groups)} vs fumbles ${JSON.stringify(categories)}`);

  r.equal(t.labelFor("fire"), "Fire", "damage type label comes from the system");
  r.equal(t.labelFor("magical"), "Magical", "category label comes from lang/en.json");
  r.equal(t.labelFor("chaos"), "Chaos", "an unknown key still renders, capitalised");

  // Every damage type belongs to exactly one bucket, or the picker drops or repeats one.
  const grouped = t.damageTypeGroups().flatMap(g => g.types);
  r.check(grouped.length === t.damageTypes().length && new Set(grouped).size === grouped.length,
    `${grouped.length} damage types, each in exactly one group`,
    `grouped ${grouped.length}, total ${t.damageTypes().length}`);

  for (const [type, expected] of [["piercing", "physical"], ["fire", "elemental"], ["radiant", "magical"]]) {
    r.equal(t.categoryFor(type), expected, `${type} buckets as ${expected}`);
  }
  r.equal(t.categoryFor("chaos"), null, "an unknown damage type has no category");

  // Fumbles accept a category directly or a damage type to bucket.
  r.equal(t.tableKeyFor("fumble", "physical"), "physical", "fumble takes a category as-is");
  r.equal(t.tableKeyFor("fumble", "piercing"), "physical", "fumble buckets a damage type");
  r.equal(t.tableKeyFor("crit", "piercing"), "piercing", "crit indexes by damage type");

  // Full coverage: a d100 must land on an entry for every table, with no gap.
  let lookups = 0;
  const gaps = [];
  for (const kind of ["crit", "fumble"]) {
    const keys = Object.keys(kind === "crit" ? tables.crits : tables.fumbles);
    for (const key of keys) {
      for (let roll = 1; roll <= 100; roll++) {
        lookups++;
        if (!t.resolveRoll(roll, kind, key)) gaps.push(`${kind}/${key} @ ${roll}`);
      }
    }
  }
  r.check(!gaps.length, `${lookups} table lookups, every roll resolved`, gaps.slice(0, 5).join(", "));
  r.equal(t.resolveRoll(101, "crit", "fire"), null, "a roll off the end of the table returns null");
  r.equal(t.resolveRoll(50, "crit", "nonsense"), null, "an unknown table returns null");

  return r.failures;
}
