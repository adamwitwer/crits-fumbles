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

/** Damage type -> fumble category. Returns null for anything not on the tables. */
export function categoryFor(damageType) {
  return CATEGORY_OF[damageType] ?? null;
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
