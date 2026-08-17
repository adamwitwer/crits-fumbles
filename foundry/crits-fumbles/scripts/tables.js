import { MODULE_ID } from "./constants.js";

/** Fumble tables bucket the 13 damage types into three categories. */
const CATEGORIES = {
  physical: ["bludgeoning", "slashing", "piercing"],
  elemental: ["acid", "cold", "fire", "lightning", "thunder"],
  magical: ["force", "necrotic", "poison", "psychic", "radiant"]
};

const CATEGORY_OF = Object.freeze(
  Object.fromEntries(
    Object.entries(CATEGORIES).flatMap(([category, types]) => types.map(t => [t, category]))
  )
);

let tables = null;

/** Load the pre-parsed tables. Called once on ready. */
export async function loadTables() {
  const path = `modules/${MODULE_ID}/data/tables.json`;
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${MODULE_ID}: could not load ${path} (${response.status})`);
  tables = await response.json();
  return tables;
}

export function getTables() {
  if (!tables) throw new Error(`${MODULE_ID}: tables not loaded yet`);
  return tables;
}

export function damageTypes() {
  return Object.keys(getTables().crits);
}

/** The fumble buckets double as the display grouping, in table order. */
export function damageTypeGroups() {
  const known = new Set(damageTypes());
  return [
    { key: "physical", label: "Physical" },
    { key: "elemental", label: "Elemental" },
    { key: "magical", label: "Magic" }
  ].map(group => ({
    ...group,
    types: CATEGORIES[group.key].filter(type => known.has(type))
  }));
}

/**
 * Display form of a table key. Keys are single lowercase words — damage types and
 * fumble categories alike — so capitalising the first letter is the whole job.
 */
export function labelFor(key) {
  return String(key).charAt(0).toUpperCase() + String(key).slice(1);
}

/** Damage type -> fumble category. Returns null for anything not on the tables. */
export function categoryFor(damageType) {
  return CATEGORY_OF[damageType] ?? null;
}

/**
 * The fumble tables are deliberately coarser than the crit tables: three categories
 * rather than thirteen damage types, matching the web app.
 */
export function fumbleCategories() {
  return Object.keys(getTables().fumbles).map(key => ({ key, label: labelFor(key) }));
}

export function isFumbleCategory(value) {
  return Object.hasOwn(getTables().fumbles, value);
}

/** Resolve a user or detected selection to the table key for `kind`. */
export function tableKeyFor(kind, selection) {
  if (kind !== "fumble") return selection;
  return isFumbleCategory(selection) ? selection : categoryFor(selection);
}

/**
 * Look up a roll on one of the tables.
 * `kind` is "crit" or "fumble"; `key` is a damage type or a fumble category.
 */
export function resolveRoll(value, kind, key) {
  const table = getTables()[kind === "crit" ? "crits" : "fumbles"]?.[key];
  if (!table) return null;
  return table.find(entry => value >= entry.min && value <= entry.max) ?? null;
}
