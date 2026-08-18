import { load, reporter, stubFoundry } from "./harness.mjs";

export const name = "condition links";

const escapeHtml = text => String(text).replace(/[&<>"']/g, ch =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));

export default async function run() {
  const { tables } = await stubFoundry();
  const r = reporter();
  const { linkConditions, enrich } = await load("conditions.js", "linked");

  let entries = 0, withLinks = 0, links = 0;
  const problems = [];

  for (const kind of ["crits", "fumbles"]) {
    for (const [key, rows] of Object.entries(tables[kind])) {
      for (const row of rows) {
        entries++;
        const escaped = escapeHtml(row.effect);
        const marked = linkConditions(escaped);
        const count = [...marked.matchAll(/@UUID\[/g)].length;
        links += count;
        if (count) withLinks++;

        if (/@UUID\[[^\]]*@UUID/.test(marked)) problems.push(`nested enricher in ${kind}/${key} @ ${row.min}`);
        // "concentrating" is a dnd5e condition, but the tables use the word in its
        // plain sense — "if concentrating on a spell, concentration ends".
        if (/\]\{concentrating\}/i.test(marked)) problems.push(`linked 'concentrating' in ${kind}/${key} @ ${row.min}`);
        // With no enricher available the fallback must give the text back untouched.
        if (await enrich(marked) !== escaped) problems.push(`lossy fallback in ${kind}/${key} @ ${row.min}`);
      }
    }
  }

  r.check(!problems.length, `${entries} entries: ${withLinks} carry links, ${links} links, none nested or lossy`,
    problems.slice(0, 3).join("; "));
  r.check(links > 0, "the tables actually produced links", "none were produced");

  // A system that offers no references leaves the text exactly as it was.
  globalThis.CONFIG = { DND5E: {} };
  const bare = await load("conditions.js", "bare");
  const plain = "The target is knocked Prone.";
  r.equal(bare.linkConditions(plain), plain, "no references in CONFIG leaves the text alone");

  // With references and a working enricher, links become anchors.
  await stubFoundry();
  globalThis.foundry = { applications: { ux: { TextEditor: { implementation: {
    enrichHTML: async html => html.replace(/@UUID\[([^\]]+)\]\{([^}]*)\}/g,
      (_, uuid, label) => `<a class="content-link" data-uuid="${uuid}">${label}</a>`)
  } } } } };
  const wired = await load("conditions.js", "wired");
  const out = await wired.enrich(wired.linkConditions("Knocked Prone and Stunned."));
  r.check(/content-link[^>]*>Prone</.test(out) && /content-link[^>]*>Stunned</.test(out),
    "both conditions become content links", out);

  // An enricher that throws must not take the card down.
  globalThis.foundry.applications.ux.TextEditor.implementation.enrichHTML = async () => { throw new Error("boom"); };
  const broken = await load("conditions.js", "broken");
  const original = console.warn;
  console.warn = () => {};
  const fallback = await broken.enrich(broken.linkConditions(plain));
  console.warn = original;
  r.equal(fallback, plain, "an enricher that throws falls back to the plain words");

  delete globalThis.foundry;
  return r.failures;
}
