import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { MODULE_DIR, readJson, reporter } from "./harness.mjs";

export const name = "localization coverage";

/** Keys built at runtime from data rather than written out in the source. */
const DYNAMIC = /^CRITSFUMBLES\.Category\./;

async function* sourceFiles(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== "data") yield* sourceFiles(path);
    } else if (/\.(js|hbs)$/.test(entry.name)) {
      yield path;
    }
  }
}

export default async function run() {
  const r = reporter();
  const lang = await readJson("lang/en.json");
  const tables = await readJson("data/tables.json");
  const defined = new Set(Object.keys(lang));

  const used = new Map();
  const inline = [];
  for await (const file of sourceFiles(MODULE_DIR)) {
    const relative = file.replace(MODULE_DIR + "/", "");
    const text = await readFile(file, "utf8");

    for (const [key] of text.matchAll(/CRITSFUMBLES\.[A-Za-z.]+/g)) {
      if (!used.has(key)) used.set(key, []);
      used.get(key).push(relative);
    }

    // User-facing English must not creep back into the render paths.
    for (const [i, line] of text.split("\n").entries()) {
      if (/^\s*(\/\/|\*|\/\*)/.test(line)) continue;
      if (/\b(name|hint|title|label):\s*"(?!CRITSFUMBLES)[A-Z]/.test(line)) {
        inline.push(`${relative}:${i + 1} ${line.trim()}`);
      }
    }
  }

  const missing = [...used.keys()].filter(key => !DYNAMIC.test(key) && !defined.has(key));
  const unused = [...defined].filter(key => !DYNAMIC.test(key) && !used.has(key));

  r.check(!missing.length, `${used.size} keys referenced, all defined`, missing.join(", "));
  r.check(!unused.length, `${defined.size} keys defined, none orphaned`, unused.join(", "));
  r.check(!inline.length, "no inline user-facing strings in the source", inline.join(" | "));

  // Category keys are built as CRITSFUMBLES.Category.${key} from the table data, so a
  // renamed fumble table would silently render a raw key.
  const categories = Object.keys(tables.fumbles);
  const missingCategories = categories.filter(key => !defined.has(`CRITSFUMBLES.Category.${key}`));
  r.check(!missingCategories.length,
    `every fumble table has a category label (${categories.join(", ")})`, missingCategories.join(", "));

  return r.failures;
}
