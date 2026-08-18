#!/usr/bin/env node
/**
 * Checks for the Foundry module's pure logic.
 *
 * The module cannot be exercised outside Foundry, so these cover the parts that decide
 * things — table lookups, damage type detection, the turn rule, condition linking, the
 * toolbar registration and localization coverage — with a stub standing in for `game`
 * and `CONFIG`. Anything needing a real canvas, socket or document is verified in a
 * world instead, and said to be unverified when it has not been.
 *
 *   node tools/check-foundry-module.mjs
 *
 * Every suite runs even if an earlier one fails, so one run shows everything at once.
 */
const SUITES = ["tables", "damage-type", "turn-gate", "trigger", "conditions", "controls", "forced-crits", "i18n"];

let failed = 0;
for (const file of SUITES) {
  const suite = await import(`./checks/${file}.mjs`);
  console.log(`\n  ${suite.name}`);

  let failures;
  try {
    failures = await suite.default();
  } catch (error) {
    console.log(`    ERROR  the suite itself threw: ${error.message}`);
    console.log(error.stack.split("\n").slice(1, 4).join("\n"));
    failed++;
    continue;
  }

  for (const failure of failures) console.log(`    FAIL ${failure}`);
  if (failures.length) failed++;
}

console.log(failed
  ? `\n  ${failed} of ${SUITES.length} suites failed\n`
  : `\n  all ${SUITES.length} suites passed\n`);
process.exit(failed ? 1 : 0);
