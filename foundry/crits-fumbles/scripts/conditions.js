import { MODULE_ID } from "./constants.js";

/**
 * Conditions the table text names, matching the set the web app links out to the
 * D&D Beyond rules glossary.
 *
 * An explicit list rather than everything in CONFIG.DND5E.conditionTypes, because
 * that config also carries "concentrating" and the tables use the word in its plain
 * sense ("if concentrating on a spell, concentration ends") three times. Linking
 * those would point at a status effect the sentence is not talking about.
 *
 * The UUIDs are not listed here: dnd5e stores a rules-compendium reference on each
 * condition, so the system supplies them and they survive a system update.
 */
const LINKED = [
  "blinded", "deafened", "frightened", "grappled", "incapacitated", "paralyzed",
  "petrified", "poisoned", "prone", "restrained", "stunned", "unconscious"
];

let cache = null;

/** Condition key -> rules-compendium UUID, for the ones this system actually offers. */
function references() {
  if (cache) return cache;

  cache = new Map();
  for (const key of LINKED) {
    const reference = globalThis.CONFIG?.DND5E?.conditionTypes?.[key]?.reference;
    if (typeof reference === "string" && reference) cache.set(key, reference);
  }
  return cache;
}

/**
 * Mark condition words in escaped table text as Foundry content links.
 *
 * The web app sent these to D&D Beyond in a new browser tab. Foundry's equivalent is
 * in the world already: the system ships the rules as a compendium journal, and an
 * @UUID reference opens that page beside the game instead of leaving it. This writes
 * the enricher syntax; `enrich` below turns it into anchors.
 *
 * Takes text that is already HTML-escaped, and any condition it cannot resolve is
 * left as the plain word it is today.
 */
export function linkConditions(text) {
  const refs = references();
  if (!refs.size || !text) return text;

  const pattern = new RegExp(`\\b(${[...refs.keys()].join("|")})\\b`, "gi");
  return String(text).replace(pattern, match => {
    const uuid = refs.get(match.toLowerCase());
    // Braces keep the table's own capitalisation rather than the system's label.
    return uuid ? `@UUID[${uuid}]{${match}}` : match;
  });
}

/**
 * Resolve enricher syntax to HTML before the message is stored.
 *
 * Done here rather than left to the chat renderer so the card carries finished markup
 * on any Foundry version, and a build without the enricher posts readable text instead
 * of raw @UUID[...] syntax.
 */
export async function enrich(html) {
  // v13 moved TextEditor under foundry.applications.ux and deprecated the global.
  const editor = globalThis.foundry?.applications?.ux?.TextEditor?.implementation ?? globalThis.TextEditor;
  if (typeof editor?.enrichHTML !== "function") return stripEnrichers(html);

  try {
    return await editor.enrichHTML(html);
  } catch (error) {
    console.warn(`${MODULE_ID} | could not enrich the card, posting it unlinked`, error);
    return stripEnrichers(html);
  }
}

/** Fall back to the bare word, so a failure never shows @UUID[...] to the table. */
function stripEnrichers(html) {
  return String(html).replace(/@UUID\[[^\]]+\]\{([^}]*)\}/g, "$1");
}

/**
 * Report whether condition links will resolve in this world.
 *
 * Written because the linking depends on two things this module cannot check offline:
 * that dnd5e still records a reference per condition, and that the rules compendium is
 * present and unlocked to this user.
 */
export async function checkConditions() {
  const rows = [];
  for (const key of LINKED) {
    const uuid = globalThis.CONFIG?.DND5E?.conditionTypes?.[key]?.reference ?? null;
    let resolves = false;
    if (uuid) {
      try {
        resolves = Boolean(await fromUuid(uuid));
      } catch {
        resolves = false;
      }
    }
    rows.push({ condition: key, uuid: uuid ?? "—", resolves });
  }

  const working = rows.filter(r => r.resolves).length;
  console.group(`${MODULE_ID} | condition links: ${working}/${rows.length} resolve`);
  console.table(rows);
  console.groupEnd();
  return rows;
}
