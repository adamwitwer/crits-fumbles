import { captureConsole, load, reporter, stubFoundry } from "./harness.mjs";

export const name = "the toolbar button";

export default async function run() {
  await stubFoundry();
  const r = reporter();

  let handler = null;
  globalThis.Hooks = { on: (event, fn) => { if (event === "getSceneControlButtons") handler = fn; } };

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

  delete globalThis.Hooks;
  return r.failures;
}
