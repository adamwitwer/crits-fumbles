import { MODULE_ID } from "./constants.js";
import { getTables, labelFor, resolveRoll, tableKeyFor } from "./tables.js";

/**
 * Roll on a table and post the result to chat.
 *
 * Deliberately ungated: the house rule limiting auto-triggers to a combatant's
 * first attack lives in the trigger, so anything calling this directly (macro,
 * dialog) works regardless of whose turn it is.
 */
export async function rollTable({ kind, damageType, actor = null, flavorPrefix = null } = {}) {
  if (kind !== "crit" && kind !== "fumble") throw new Error(`${MODULE_ID}: kind must be "crit" or "fumble"`);

  // Crits index by damage type. Fumbles index by category, and accept either a
  // category chosen directly or a damage type to bucket.
  const key = tableKeyFor(kind, damageType);
  if (!key) throw new Error(`${MODULE_ID}: no ${kind} table for "${damageType}"`);

  const roll = await new Roll(`1d${getTables().die}`).evaluate();
  const entry = resolveRoll(roll.total, kind, key);

  const label = game.i18n.localize(kind === "crit" ? "CRITSFUMBLES.CriticalHit" : "CRITSFUMBLES.Fumble");
  const flavor = [flavorPrefix, `${label} — ${labelFor(key)}`].filter(Boolean).join(" ");

  await ChatMessage.create({
    speaker: ChatMessage.getSpeaker(actor ? { actor } : {}),
    flavor,
    rolls: [roll],
    content: renderCard({ kind, key, roll, entry })
  });

  return { roll, entry };
}

function renderCard({ kind, key, roll, entry }) {
  const title = entry ? entry.title : game.i18n.localize("CRITSFUMBLES.NoResult");
  const effect = entry ? entry.effect : `No table entry matched ${roll.total}.`;

  // Built as a string rather than a Handlebars template so this milestone depends
  // on no template-loading API; swap for a .hbs once the UI settles.
  return `
    <div class="crits-fumbles-card" data-kind="${kind}">
      <header><span class="cf-roll">${roll.total}</span> <span class="cf-type">${escapeHtml(key)}</span></header>
      <h4>${escapeHtml(title)}</h4>
      <p>${escapeHtml(effect)}</p>
    </div>
  `.trim();
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));
}
