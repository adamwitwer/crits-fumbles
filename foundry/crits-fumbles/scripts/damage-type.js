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
  const found = [];

  const push = value => {
    if (typeof value === "string" && value) found.push(value.toLowerCase());
  };
  const pushAll = value => {
    if (!value) return;
    if (value instanceof Set || Array.isArray(value)) value.forEach(push);
    else push(value);
  };

  // Activity damage parts (dnd5e 4.x / 5.x): each part carries a `types` Set.
  for (const part of activity?.damage?.parts ?? []) {
    pushAll(part?.types);
    push(part?.type);
  }

  // A weapon's base damage, which an attack activity folds in rather than repeating.
  const base = activity?.item?.system?.damage?.base;
  pushAll(base?.types);
  push(base?.type);

  // Legacy (dnd5e 3.x) shape: system.damage.parts is [[formula, type], ...].
  const legacy = activity?.item?.system?.damage?.parts;
  if (Array.isArray(legacy)) {
    for (const part of legacy) if (Array.isArray(part)) push(part[1]);
  }

  return [...new Set(found)];
}

export function logMiss(activity, seen) {
  console.warn(
    `${MODULE_ID} | no table damage type for "${activity?.item?.name ?? "unknown item"}". ` +
    `Saw: ${seen.length ? seen.join(", ") : "(nothing)"}. Activity:`,
    activity
  );
}
