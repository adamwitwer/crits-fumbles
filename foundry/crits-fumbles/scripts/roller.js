import { MODULE_ID } from "./constants.js";
import { categoryFor, getTables, resolveRoll } from "./tables.js";

/**
 * Roll on a table and post the result to chat.
 *
 * Deliberately ungated: the house rule limiting auto-triggers to a combatant's
 * first attack lives in the trigger, so anything calling this directly (macro,
 * dialog) works regardless of whose turn it is.
 */
export async function rollTable({ kind, damageType, actor = null, flavorPrefix = null } = {}) {
  if (kind !== "crit" && kind !== "fumble") throw new Error(`${MODULE_ID}: kind must be "crit" or "fumble"`);

  // Crits index by damage type; fumbles index by the category it falls in.
  const key = kind === "crit" ? damageType : categoryFor(damageType);
  if (!key) throw new Error(`${MODULE_ID}: no ${kind} table for damage type "${damageType}"`);

  const roll = await new Roll(`1d${getTables().die}`).evaluate();
  const entry = resolveRoll(roll.total, kind, key);

  const label = game.i18n.localize(kind === "crit" ? "CRITSFUMBLES.CriticalHit" : "CRITSFUMBLES.Fumble");
  const flavor = [flavorPrefix, `${label} — ${damageType}`].filter(Boolean).join(" ");

  await ChatMessage.create({
    speaker: ChatMessage.getSpeaker(actor ? { actor } : {}),
    flavor,
    rolls: [roll],
    content: renderCard({ kind, damageType, roll, entry })
  });

  return { roll, entry };
}

function renderCard({ kind, damageType, roll, entry }) {
  const title = entry ? entry.title : game.i18n.localize("CRITSFUMBLES.NoResult");
  const effect = entry ? entry.effect : `No table entry matched ${roll.total}.`;

  // Built as a string rather than a Handlebars template so this milestone depends
  // on no template-loading API; swap for a .hbs once the UI settles.
  return `
    <div class="crits-fumbles-card" data-kind="${kind}">
      <header><span class="cf-roll">${roll.total}</span> <span class="cf-type">${escapeHtml(damageType)}</span></header>
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
