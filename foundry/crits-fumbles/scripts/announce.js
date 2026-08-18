import { MODULE_ID, t } from "./constants.js";
import { rollTable } from "./roller.js";
import { categoryFor, damageTypeGroups, fumbleCategories, labelFor } from "./tables.js";

const FLAG = "announcement";

const STYLE = {
  crit: { emoji: "💥", key: "CRITSFUMBLES.CriticalHit" },
  fumble: { emoji: "💀", key: "CRITSFUMBLES.Fumble" }
};

/**
 * Announce a crit or fumble in chat with an inline selector.
 *
 * Posting to chat rather than opening a dialog keeps the moment visible to the whole
 * table and leaves a record in the log, and it does not steal focus from whoever is
 * mid-turn. The roll happens when someone resolves the card.
 */
export async function announce({ actor, kind, detected = [] }) {
  const options = optionsFor(kind, detected);

  await ChatMessage.create({
    speaker: ChatMessage.getSpeaker(actor ? { actor } : {}),
    content: renderAnnouncement({ kind, options }),
    flags: {
      [MODULE_ID]: {
        [FLAG]: {
          kind,
          actorUuid: actor?.uuid ?? null,
          resolved: false
        }
      }
    }
  });
}

/**
 * Crits offer the thirteen damage types grouped as on the crit tables; fumbles offer
 * the three fumble categories, which is the coarser split the tables actually use.
 * Detected types are preselected — mapped through to categories for fumbles.
 */
function optionsFor(kind, detected) {
  const found = new Set(detected);

  if (kind === "fumble") {
    return [{
      label: null,
      items: fumbleCategories().map(({ key, label }) => ({
        value: key,
        label,
        detected: [...found].some(type => categoryFor(type) === key)
      }))
    }];
  }

  return damageTypeGroups().map(group => ({
    label: group.label,
    items: group.types.map(type => ({
      value: type,
      label: labelFor(type),
      detected: found.has(type)
    }))
  }));
}

function renderAnnouncement({ kind, options }) {
  const { emoji, key } = STYLE[kind] ?? STYLE.crit;
  const preselected = options.flatMap(g => g.items).find(item => item.detected);
  // A fumble is rolled by category, not by damage type; the label must not claim otherwise.
  const fieldLabel = t(kind === "fumble" ? "CRITSFUMBLES.FumbleCategory" : "CRITSFUMBLES.DamageType");

  const optionGroups = options.map(group => {
    const items = group.items.map(item =>
      `<option value="${item.value}"${item.value === preselected?.value ? " selected" : ""}>` +
      `${escapeHtml(item.label)}${item.detected ? " ●" : ""}</option>`
    ).join("");
    return group.label ? `<optgroup label="${escapeHtml(group.label)}">${items}</optgroup>` : items;
  }).join("");

  return `
    <div class="crits-fumbles-announce" data-kind="${kind}">
      <h3 class="cf-headline">${emoji} ${escapeHtml(t(key))} ${emoji}</h3>
      <div class="cf-choose">
        <label>
          <span>${escapeHtml(fieldLabel)}</span>
          <select class="cf-select" name="selection">${optionGroups}</select>
        </label>
        <button type="button" class="cf-roll-button">${escapeHtml(t("CRITSFUMBLES.Roll"))}</button>
      </div>
      ${preselected ? `<p class="cf-note">${escapeHtml(t("CRITSFUMBLES.DetectedNote"))}</p>` : ""}
    </div>
  `.trim();
}

/**
 * Wire the card's controls.
 *
 * Delegated from the document rather than hooked into chat rendering: the render hook
 * was renamed in v13 and its jQuery signature deprecated, while a delegated listener
 * works the same on every version and covers messages re-rendered at any time.
 */
export function registerAnnouncementListeners() {
  document.addEventListener("click", event => {
    const button = event.target.closest?.(".crits-fumbles-announce .cf-roll-button");
    if (!button) return;
    event.preventDefault();
    onResolve(button).catch(error => console.error(`${MODULE_ID} | resolving announcement failed`, error));
  });
}

async function onResolve(button) {
  const card = button.closest(".crits-fumbles-announce");
  const messageId = button.closest("[data-message-id]")?.dataset?.messageId;
  const message = game.messages.get(messageId);
  if (!message) return;

  const state = message.getFlag(MODULE_ID, FLAG);
  if (!state || state.resolved) return;

  if (!canResolve(message)) {
    ui.notifications.warn(t("CRITSFUMBLES.NotYours"));
    return;
  }

  const selection = card.querySelector(".cf-select")?.value;
  if (!selection) return;

  // Mark resolved before rolling so a double click cannot roll twice.
  await message.setFlag(MODULE_ID, FLAG, { ...state, resolved: true, selection });
  await message.update({ content: renderResolved({ kind: state.kind, selection }) });

  const actor = state.actorUuid ? await fromUuid(state.actorUuid) : null;
  await rollTable({
    kind: state.kind,
    damageType: selection,
    actor,
    flavorPrefix: actor?.name ?? null
  });
}

/** The attacker or a GM. Everyone else sees the card but cannot roll it. */
function canResolve(message) {
  return game.user.isGM || message.isAuthor;
}

function renderResolved({ kind, selection }) {
  const { emoji, key } = STYLE[kind] ?? STYLE.crit;
  const rolled = t("CRITSFUMBLES.RolledOn", { table: labelFor(selection) });
  return `
    <div class="crits-fumbles-announce cf-resolved" data-kind="${kind}">
      <h3 class="cf-headline">${emoji} ${escapeHtml(t(key))} ${emoji}</h3>
      <p class="cf-note">${escapeHtml(rolled)}</p>
    </div>
  `.trim();
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));
}
