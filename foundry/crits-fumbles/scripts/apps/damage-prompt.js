import { MODULE_ID, t } from "../constants.js";
import { categoryFor, damageTypeGroups, fumbleCategories, labelFor } from "../tables.js";

const { ApplicationV2, HandlebarsApplicationMixin } = foundry.applications.api;

/**
 * Asks which damage type an attack dealt.
 *
 * The system cannot know: a monk's unarmed strike carries both bludgeoning and force
 * and the player picks at will, and that pattern repeats across classes. Detected
 * types are marked so the common case is still one click, but the choice is the
 * user's. Picking a type rolls immediately — there is no second confirm step, because
 * this appears mid-combat.
 */
class DamagePrompt extends HandlebarsApplicationMixin(ApplicationV2) {
  static DEFAULT_OPTIONS = {
    id: "crits-fumbles-damage-prompt",
    classes: ["crits-fumbles", "crits-fumbles-prompt"],
    tag: "div",
    window: { title: "CRITSFUMBLES.Title", icon: "fa-solid fa-burst" },
    position: { width: 460, height: "auto" },
    actions: {
      pick: DamagePrompt.#onPick,
      kind: DamagePrompt.#onKind
    }
  };

  static PARTS = {
    body: { template: `modules/${MODULE_ID}/templates/damage-prompt.hbs` }
  };

  #resolve;
  #settled = false;
  #kind;

  constructor(options = {}) {
    super(options);
    this.#resolve = options.resolve;
    this.#kind = options.kind ?? "crit";
  }

  get title() {
    const what = t(this.#kind === "crit" ? "CRITSFUMBLES.CriticalHit" : "CRITSFUMBLES.Fumble");
    const who = this.options.actorName;
    return who ? `${what} — ${who}` : what;
  }

  async _prepareContext() {
    const isCrit = this.#kind === "crit";
    const detected = new Set(this.options.detected ?? []);

    // Fumble tables are deliberately coarser: three categories, not thirteen types.
    // Detected damage types are mapped through so a bludgeoning/force strike
    // highlights Physical and Magical.
    const groups = isCrit
      ? damageTypeGroups().map(group => ({
          label: group.label,
          types: group.types.map(type => ({
            type,
            label: labelFor(type),
            detected: detected.has(type)
          }))
        }))
      : [{
          label: null,
          types: fumbleCategories().map(({ key, label }) => ({
            type: key,
            label,
            detected: [...detected].some(type => categoryFor(type) === key)
          }))
        }];

    return {
      kind: this.#kind,
      isCrit,
      lockedKind: !!this.options.lockKind,
      anyDetected: groups.some(group => group.types.some(type => type.detected)),
      groups
    };
  }

  static #onPick(event, target) {
    this.#settle(target.dataset.type);
  }

  static #onKind(event, target) {
    this.#kind = target.dataset.kind === "fumble" ? "fumble" : "crit";
    this.render();
  }

  #settle(damageType) {
    if (this.#settled) return;
    this.#settled = true;
    this.#resolve?.({ kind: this.#kind, damageType });
    this.close();
  }

  async close(options) {
    if (!this.#settled) {
      this.#settled = true;
      this.#resolve?.(null); // dismissed without choosing
    }
    return super.close(options);
  }
}

/**
 * Show the prompt and resolve with { kind, damageType }, or null if dismissed.
 * Never throws: a broken dialog must not swallow a critical hit.
 */
export async function promptForDamageType({ kind = "crit", detected = [], actorName = null, lockKind = true } = {}) {
  try {
    return await new Promise(resolve => {
      new DamagePrompt({ kind, detected, actorName, lockKind, resolve }).render(true);
    });
  } catch (error) {
    console.error(`${MODULE_ID} | damage type prompt failed`, error);
    return null;
  }
}
