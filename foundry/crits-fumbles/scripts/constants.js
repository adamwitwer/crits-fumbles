/** Must match the module.json "id" and the folder name under Data/modules. */
export const MODULE_ID = "crits-fumbles";

/**
 * Localize a key, optionally with {placeholders}.
 *
 * Wrapped rather than calling game.i18n directly so the module's strings can be read
 * outside a running Foundry — the table and label logic is checked in Node, where
 * `game` does not exist.
 */
export function t(key, data = null) {
  const i18n = globalThis.game?.i18n;
  if (!i18n) return key;
  return data ? i18n.format(key, data) : i18n.localize(key);
}
