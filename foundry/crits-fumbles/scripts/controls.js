import { MODULE_ID } from "./constants.js";

/** The Token group, where v13+ keys its scene controls. Was "token" in v12. */
const GROUP = "tokens";
const TOOL = "critsFumbles";

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
}

/** Sit after the core tools rather than competing with them for a slot. */
function nextOrder(tools) {
  const orders = Object.values(tools).map(tool => Number(tool?.order)).filter(Number.isFinite);
  return orders.length ? Math.max(...orders) + 1 : 0;
}
