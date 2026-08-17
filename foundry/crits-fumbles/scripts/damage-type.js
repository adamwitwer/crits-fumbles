import { MODULE_ID } from "./constants.js";
import { damageTypes } from "./tables.js";

/**
 * Work out which damage type an attack deals.
 *
 * The activity damage schema has moved across dnd5e versions and is the one part of
 * this module that could not be settled from documentation, so every known shape is
 * tried and the first recognised type wins. `collect` returns everything it saw so a
 * miss can be diagnosed from the log rather than guessed at.
 */
export function damageTypeFor(activity) {
  const known = new Set(damageTypes());
  const seen = collect(activity);
  const match = seen.find(type => known.has(type)) ?? null;
  return { damageType: match, seen };
}

function collect(activity) {
  const into = target => {
    const push = value => {
      if (typeof value === "string" && value) target.push(value.toLowerCase());
    };
    return value => {
      if (!value) return;
      if (value instanceof Set || Array.isArray(value)) value.forEach(push);
      else push(value);
    };
  };

  // Activity damage parts (dnd5e 4.x / 5.x): each part carries a `types` Set.
  const fromParts = [];
  const addPart = into(fromParts);
  for (const part of activity?.damage?.parts ?? []) {
    addPart(part?.types);
    addPart(part?.type);
  }

  // The weapon's own base damage, which an attack folds in rather than repeating.
  const fromBase = [];
  const addBase = into(fromBase);
  const base = activity?.item?.system?.damage?.base;
  addBase(base?.types);
  addBase(base?.type);

  // Legacy (dnd5e 3.x) shape: system.damage.parts is [[formula, type], ...].
  const fromLegacy = [];
  const addLegacy = into(fromLegacy);
  const legacy = activity?.item?.system?.damage?.parts;
  if (Array.isArray(legacy)) {
    for (const part of legacy) if (Array.isArray(part)) addLegacy(part[1]);
  }

  // includeBase means the activity deals the weapon's base damage plus its own parts,
  // so the base is the attack's primary type and the parts are riders on top of it —
  // a flame tongue's fire rider must not outrank its slashing base. Without it the
  // activity defines the damage outright and its parts lead.
  const ordered = activity?.damage?.includeBase === true
    ? [...fromBase, ...fromParts]
    : [...fromParts, ...fromBase];

  return [...new Set([...ordered, ...fromLegacy])];
}

export function logMiss(activity, seen) {
  console.warn(
    `${MODULE_ID} | no table damage type for "${activity?.item?.name ?? "unknown item"}". ` +
    `Saw: ${seen.length ? seen.join(", ") : "(nothing)"}. Activity:`,
    activity
  );
}
