import { captureConsole, load, reporter, stubFoundry } from "./harness.mjs";

export const name = "the toolbar button";

export default async function run() {
  await stubFoundry();
  const r = reporter();

  const hooks = {};
  globalThis.Hooks = { on: (event, fn) => { hooks[event] = fn; } };
  const handler = (...args) => hooks.getSceneControlButtons(...args);
  const render = (...args) => hooks.renderSceneControls(...args);

  const { registerSceneControl } = await load("controls.js", "controls");
  let opened = 0;
  registerSceneControl(async () => { opened++; });

  // The v13+/v14 record shape: controls keyed by name, tools keyed by name.
  const controls = { tokens: { name: "tokens", tools: {
    select: { name: "select", order: 0 }, target: { name: "target", order: 1 }, ruler: { name: "ruler", order: 2 }
  } } };
  handler(controls);
  const tool = controls.tokens.tools.critsFumbles;

  r.check(!!tool, "the tool is added under controls.tokens.tools");
  if (tool) {
    r.equal(tool.icon, "fa-solid fa-burst", "the icon matches the picker window");
    r.equal(tool.button, true, "it is a button, not a toggle");
    r.equal(tool.visible, true, "players can see it — this is the on-demand roll");
    r.equal(tool.title, "CRITSFUMBLES.Title", "the tooltip is a localization key");
    r.equal(tool.order, 3, "it sits after the core tools");
    // foundryvtt#12761: core reads onChange on click and throws without it.
    r.equal(typeof tool.onChange, "function", "onChange exists, or core throws on click");

    tool.onChange();
    await new Promise(resolve => setImmediate(resolve));
    r.equal(opened, 1, "clicking it opens the picker");
  }

  // A picker that rejects must not throw inside a core render.
  registerSceneControl(async () => { throw new Error("boom"); });
  const empty = { tokens: { tools: {} } };
  handler(empty);
  const captured = await captureConsole(async () => {
    empty.tokens.tools.critsFumbles.onChange();
    await new Promise(resolve => setImmediate(resolve));
  });
  r.check(captured.error.some(line => line.includes("opening the picker failed")),
    "a failing picker is caught and logged, not thrown at core", JSON.stringify(captured.error));
  r.equal(empty.tokens.tools.critsFumbles.order, 0, "an empty tool group still yields a valid order");

  // If a later version renames or moves the group, say so rather than throwing.
  const missing = await captureConsole(async () => {
    handler({ someOtherGroup: { tools: {} } });
    handler({});
    handler(undefined);
  });
  r.equal(missing.warn.length, 3, "a missing control group warns once per render, and never throws");
  r.check(missing.warn.every(line => line.includes("CritsFumbles.open()")),
    "the warning points at the macro that still works", JSON.stringify(missing.warn));

  // --- the hover tooltip ---
  // Which attribute a build honours can only be settled in Foundry, so both are set.
  // What is checkable here is that both carry the same words, and that neither throws.
  const button = { dataset: {} };
  const root = { querySelector: selector => (selector.includes("critsFumbles") ? button : null) };
  render({}, root);

  r.check(button.dataset.tooltipHtml?.startsWith("<h1>Crits &amp; Fumbles</h1>"),
    "the markup tooltip leads with the headline, ampersand escaped", button.dataset.tooltipHtml);
  r.check(button.dataset.tooltipHtml?.includes("<p>A critical hit and fumble table tied to the 5e conditions.</p>"),
    "and carries the description");
  r.check(button.dataset.tooltipHtml?.includes("<p>See Game Settings for options.</p>"),
    "and points at the settings");
  r.check(!button.dataset.tooltipHtml?.includes("CRITSFUMBLES."),
    "no unlocalized key leaked into it", button.dataset.tooltipHtml);
  r.check(button.dataset.tooltip?.includes("A critical hit and fumble table")
    && button.dataset.tooltip?.includes("See Game Settings"),
    "the plain fallback says the same thing on one line", button.dataset.tooltip);
  r.check(!/[<>]/.test(button.dataset.tooltip ?? "<"),
    "and carries no markup, for a build that escapes it", button.dataset.tooltip);
  r.equal(button.dataset.tooltipClass, "crits-fumbles-tooltip", "it is styled by our own class");
  r.equal(button.dataset.tooltipDirection, "RIGHT", "and opens away from the left-hand toolbar");

  // jQuery in older versions, a bare element in v13+.
  const wrapped = { dataset: {} };
  render({}, [{ querySelector: () => wrapped }]);
  r.check(!!wrapped.dataset.tooltipHtml, "a jQuery-wrapped render argument is unwrapped");

  // Tools render only for the open control group, so an absent button is routine.
  const quiet = await captureConsole(async () => {
    render({}, { querySelector: () => null });
    render({}, undefined);
  });
  r.check(!quiet.warn.length && !quiet.error.length,
    "a button that is not on screen is skipped silently, and never throws", JSON.stringify(quiet));

  delete globalThis.Hooks;
  return r.failures;
}
