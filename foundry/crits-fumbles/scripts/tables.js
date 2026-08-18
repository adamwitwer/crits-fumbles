import { MODULE_ID, t } from "./constants.js";

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
  return Object.keys(CATEGORIES).map(key => ({
    key,
    label: categoryLabel(key),
    types: CATEGORIES[key].filter(type => known.has(type))
  }));
}

/**
 * One name per bucket. The crit picker groups its thirteen types under these and the
 * fumble list is these, so they have to agree — they used to read "Magic" in one place
 * and "Magical" in the other.
 */
function categoryLabel(key) {
  return t(`CRITSFUMBLES.Category.${key}`);
}

/**
 * Display form of a table key, which may be a damage type or a fumble category.
 *
 * dnd5e already names and localizes the damage types, so take its label rather than
 * inventing a second spelling of "Bludgeoning" that could drift from the character
 * sheet. The categories are this module's own, and the plain capitalisation is the
 * last resort for a key the system has never heard of.
 */
export function labelFor(key) {
  const system = globalThis.CONFIG?.DND5E?.damageTypes?.[key]?.label;
  if (system) return system;
  if (Object.hasOwn(CATEGORIES, key)) return categoryLabel(key);
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
  return Object.keys(getTables().fumbles).map(key => ({ key, label: categoryLabel(key) }));
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
