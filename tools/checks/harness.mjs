import { readFile } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
export const MODULE_DIR = join(HERE, "../../foundry/crits-fumbles");
export const MODULE_URL = pathToFileURL(MODULE_DIR + "/");

/** Import a module script. `bust` forces a fresh copy when a suite needs new globals. */
export function load(path, bust = "") {
  return import(new URL(`scripts/${path}`, MODULE_URL).href + (bust ? `?${bust}` : ""));
}

export async function readJson(relative) {
  return JSON.parse(await readFile(join(MODULE_DIR, relative), "utf8"));
}

/**
 * Enough of Foundry to exercise the pure logic.
 *
 * Deliberately shallow: these checks cover the table, label, damage type and turn
 * rule decisions, which are the parts that have actually held bugs. Anything that
 * needs a real canvas, socket or document belongs in a world, not here.
 */
export async function stubFoundry({ conditions = true, damageTypes = true } = {}) {
  const lang = await readJson("lang/en.json");
  const tables = await readJson("data/tables.json");

  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => tables });

  globalThis.game = {
    i18n: {
      localize: key => lang[key] ?? key,
      format: (key, data) => (lang[key] ?? key).replace(/\{(\w+)\}/g, (_, n) => data[n])
    }
  };

  const DND5E = {};
  if (damageTypes) {
    DND5E.damageTypes = Object.fromEntries(Object.keys(tables.crits).map(key =>
      [key, { label: key[0].toUpperCase() + key.slice(1) }]));
  }
  if (conditions) {
    DND5E.conditionTypes = Object.fromEntries([
      "blinded", "charmed", "concentrating", "deafened", "exhaustion", "frightened",
      "grappled", "incapacitated", "invisible", "paralyzed", "petrified", "poisoned",
      "prone", "restrained", "stunned", "unconscious"
    ].map((key, i) => [key, {
      label: key,
      reference: `Compendium.dnd5e.content24.JournalEntry.phbAppendixCRule.JournalEntryPage.STUB${i}`
    }]));
  }
  globalThis.CONFIG = { DND5E };

  return { lang, tables };
}

/** Collects results so one failure does not hide the rest of a suite. */
export function reporter() {
  const failures = [];
  return {
    failures,
    ok: message => console.log(`    ok   ${message}`),
    check(condition, message, detail = "") {
      if (condition) console.log(`    ok   ${message}`);
      else failures.push(`${message}${detail ? ` — ${detail}` : ""}`);
    },
    equal(actual, expected, message) {
      this.check(actual === expected, message, `got ${JSON.stringify(actual)}, want ${JSON.stringify(expected)}`);
    }
  };
}

/** Silence and capture console output while a block runs. */
export async function captureConsole(fn) {
  const captured = { log: [], warn: [], error: [] };
  const original = { log: console.log, warn: console.warn, error: console.error };
  for (const level of Object.keys(captured)) {
    console[level] = (...args) => captured[level].push(args.join(" "));
  }
  try {
    await fn();
  } finally {
    Object.assign(console, original);
  }
  return captured;
}
