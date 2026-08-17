import { MODULE_ID } from "./constants.js";

/**
 * Reports what this Foundry build actually offers.
 *
 * Foundry v14 and dnd5e 5.x are both newer than the docs the rest of this module
 * was written against, and the official v14 migration notes are not published yet.
 * Rather than guess at the scene-control, template and keybinding APIs, this prints
 * what is present so the remaining features can be written against facts.
 *
 * Delete once the module no longer needs it.
 */
export function runProbe() {
  const has = path => {
    try {
      return path.split(".").reduce((o, k) => o?.[k], globalThis) !== undefined;
    } catch {
      return false;
    }
  };

  const report = {
    "foundry.version": game.version ?? game.data?.version ?? "unknown",
    "foundry.generation": game.release?.generation ?? "unknown",
    "system.id": game.system?.id ?? "unknown",
    "system.version": game.system?.version ?? "unknown",
    "ApplicationV2": has("foundry.applications.api.ApplicationV2"),
    "HandlebarsApplicationMixin": has("foundry.applications.api.HandlebarsApplicationMixin"),
    "DialogV2": has("foundry.applications.api.DialogV2"),
    "handlebars.renderTemplate": has("foundry.applications.handlebars.renderTemplate"),
    "global renderTemplate": typeof globalThis.renderTemplate === "function",
    "game.keybindings": has("game.keybindings"),
    "ui.controls": has("ui.controls"),
    "dice3d (Dice So Nice)": has("game.dice3d")
  };

  console.group(`${MODULE_ID} | environment probe`);
  console.table(report);
  console.groupEnd();

  return report;
}

/**
 * Passive listener: logs the shape of an attack roll without acting on it.
 *
 * The one part of the auto-trigger that could not be verified from docs is how to
 * read an attack's damage types off the Activity in dnd5e 5.x. Turn this on, make
 * one attack, and the console shows exactly what is available.
 */
export function watchAttacks() {
  Hooks.on("dnd5e.rollAttack", (rolls, data) => {
    const roll = rolls?.[0];
    const activity = data?.subject;

    console.group(`${MODULE_ID} | dnd5e.rollAttack observed`);
    console.log("roll.total:", roll?.total, "| isCritical:", roll?.isCritical, "| isFumble:", roll?.isFumble);
    console.log("activity type:", activity?.type, "| name:", activity?.name);
    console.log("activity.damage:", activity?.damage);
    console.log("activity.item?.system?.damage:", activity?.item?.system?.damage);
    console.log("actor:", activity?.actor?.name, "| id:", activity?.actor?.id);
    console.log("full activity (expand to explore):", activity);
    console.groupEnd();
  });
}
