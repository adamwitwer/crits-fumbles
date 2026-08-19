import { escapeHtml, MODULE_ID, t } from "./constants.js";

/** The Token group, where v13+ keys its scene controls. Was "token" in v12. */
const GROUP = "tokens";
const TOOL = "critsFumbles";
const TOOLTIP_CLASS = "crits-fumbles-tooltip";

/**
 * Put the picker on the scene control toolbar, up the left-hand side.
 *
 * Added to the Token group rather than as its own control category: a new category
 * still hits foundryvtt#12258, where the category's activeTool is never registered
 * because #prepareControls runs before this hook fires.
 *
 * `open` is passed in rather than imported to keep this file free of the roll path —
 * it registers a button and knows nothing about tables.
 */
export function registerSceneControl(open) {
  Hooks.on("getSceneControlButtons", controls => {
    const tools = controls?.[GROUP]?.tools;

    // v13 changed controls from an array to a record keyed by name. If a later version
    // moves it again, say so plainly rather than throwing inside a core render.
    if (!tools) {
      console.warn(
        `${MODULE_ID} | no "${GROUP}" scene control group, so no toolbar button. ` +
        `Use the CritsFumbles.open() macro instead.`
      );
      return;
    }

    tools[TOOL] = {
      name: TOOL,
      title: "CRITSFUMBLES.Title",
      icon: "fa-solid fa-burst",
      order: nextOrder(tools),
      button: true,
      // Players need this as much as the GM — it is the on-demand roll.
      visible: true,
      // Required, not optional: core reads onChange on click and throws without it
      // (foundryvtt#12761, closed as not planned).
      onChange: () => {
        open().catch(error => console.error(`${MODULE_ID} | opening the picker failed`, error));
      }
    };
  });

  // The tool's own `title` is a single localized string, so the headline is applied to
  // the rendered button instead. Re-applied on every render: the toolbar is rebuilt
  // when the active control group changes.
  Hooks.on("renderSceneControls", (application, element) => {
    try {
      describeButton(element);
    } catch (error) {
      console.warn(`${MODULE_ID} | could not enrich the toolbar tooltip`, error);
    }
  });
}

/**
 * Attach the two-part tooltip to the rendered button.
 *
 * Both `data-tooltip-html` and `data-tooltip` are set on purpose. v13 began treating
 * `data-tooltip` as plain text and added `data-tooltip-html` for markup, but this
 * build is ahead of the published docs and the split has not been confirmed on it. A
 * version that honours the markup shows the headline; one that does not falls back to
 * the same words on one line, rather than to nothing. `CritsFumbles.checkTooltip()`
 * reports which one the running build actually used.
 */
function describeButton(element) {
  // v13+ hands ApplicationV2 render hooks a bare element; older ones a jQuery object.
  // Duck-typed rather than tested against HTMLElement, which is not a global everywhere
  // this file is loaded — an undeclared identifier throws even behind optional chaining.
  const root = typeof element?.querySelector === "function" ? element : element?.[0];
  const button = root?.querySelector?.(`[data-tool="${TOOL}"]`);

  // Tools render only for the open control group, so an absent button is the normal
  // case whenever another group is selected. Not a problem, and not worth a warning.
  if (!button) return;

  const title = t("CRITSFUMBLES.Title");
  const description = t("CRITSFUMBLES.Tooltip.Description");
  const settings = t("CRITSFUMBLES.Tooltip.Settings");

  button.dataset.tooltipHtml =
    `<h1>${escapeHtml(title)}</h1>` +
    `<p>${escapeHtml(description)}</p>` +
    `<p>${escapeHtml(settings)}</p>`;
  button.dataset.tooltip = `${title} — ${description} ${settings}`;
  button.dataset.tooltipClass = TOOLTIP_CLASS;
  // The toolbar runs up the left edge, so the tooltip opens away from it.
  button.dataset.tooltipDirection = "RIGHT";
}

/**
 * Report what the tooltip actually became, since which attribute a build honours is
 * the one thing that cannot be settled outside Foundry.
 */
export function checkTooltip() {
  const button = document.querySelector(`[data-tool="${TOOL}"]`);
  if (!button) {
    console.warn(
      `${MODULE_ID} | tooltip: the button is not on screen. Open the Token control ` +
      `group in the scene toolbar, then run this again.`
    );
    return null;
  }

  const report = {
    "data-tooltip-html": button.dataset.tooltipHtml ?? "(unset)",
    "data-tooltip": button.dataset.tooltip ?? "(unset)",
    "data-tooltip-class": button.dataset.tooltipClass ?? "(unset)",
    tooltipManager: globalThis.game?.tooltip?.constructor?.name ?? "(none)"
  };
  console.log(`${MODULE_ID} | tooltip attributes on the toolbar button:`);
  console.table(report);
  console.log("Hover the button and inspect #tooltip: an <h1> inside means the markup path won.");
  return report;
}

/** Sit after the core tools rather than competing with them for a slot. */
function nextOrder(tools) {
  const orders = Object.values(tools).map(tool => Number(tool?.order)).filter(Number.isFinite);
  return orders.length ? Math.max(...orders) + 1 : 0;
}
