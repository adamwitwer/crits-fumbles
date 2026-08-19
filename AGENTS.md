# Working notes

Context for anyone (human or agent) changing this codebase. The README covers what the
app does; this file covers the things that are easy to get wrong and are not obvious
from reading the source.

## Local dev loop

There is no test suite. Exercise the app through Flask's test client:

```bash
# from the repo root; note the module path is app.app, and `app` is a namespace package
LOG_STORAGE_DIR=/tmp/scratch venv/bin/python -c "
from app.app import app
app.config['DISABLE_RATE_LIMITING'] = True
c = app.test_client()
print(c.post('/roll', json={'rollContext':'primary','rollType':'crit',
                            'critSource':'Fury & Folly','damageType':'fire'}).get_json())
"
```

Two habits worth keeping:

- **Always set `LOG_STORAGE_DIR`** to a scratch directory. Without it the app appends to
  the real `narrative_dice_log.jsonl` in the repo root, polluting a file that mirrors
  production history.
- **Use documentation-range IPs** (`198.51.100.x`, `203.0.113.x`) when testing anything
  IP-related. Python classifies them as private, so `IPRedactor` short-circuits and no
  real request goes to ip-api.com. Using a routable address like `8.8.8.8` in a loop will
  fire live third-party traffic and can trip their 45 req/min cap.

Re-importing `app.app` inside one process (to compare configurations) needs care:
`app.py` appends its own directory to `sys.path`, which then shadows the `app` package
and makes the next `import app.app` fail with "app is not a package". Snapshot
`sys.path` before the first import and restore it between reloads.

JS has no build step or linter. Syntax-check modules with:

```bash
cp app/static/js/main.js /tmp/m.mjs && node --check /tmp/m.mjs
```

## Footguns

**The CSP pins a hash of the inline script in `index.html`.** `add_security_headers` in
`app.py` contains `'sha256-...'` covering the `window.CF_CONFIG` block. Edit that block —
even whitespace — and the browser silently refuses to run it, breaking every JS-driven
feature while the page still renders. Recompute after any change:

```bash
LOG_STORAGE_DIR=/tmp/scratch venv/bin/python -c "
import hashlib, base64, re
from app.app import app
html = app.test_client().get('/').get_data(as_text=True)
body = re.search(r'<script>(.*?)</script>', html, re.S).group(1)
print(base64.b64encode(hashlib.sha256(body.encode()).digest()).decode())
"
```

**`render.yaml` drifts from the deployed service unless you maintain it by hand.** Render
never writes dashboard changes back into the blueprint, and nothing in CI compares them.
As of 2026-08-02 the file was reconciled against the live service (`crits-fumbles`,
`srv-d03dba6uk2gs73fko0d0`): it had the wrong service name, an empty `buildCommand`, no
disk, no `LOG_STORAGE_DIR`, and a `FLASK_ENV` that production does not set and no code
reads. Change anything in the dashboard — instance type, region, build command, disk
size — and update this file in the same breath.

The Chronicles log lives on a 1 GB disk at `/var/data`. `LOG_STORAGE_DIR` must point
there; the app now logs a warning at startup if the variable is unset, because the `.`
fallback is ephemeral and an amnesiac deploy otherwise looks perfectly healthy.

One deliberate omission: production also sets `DISCORD_WEBHOOK_URL`, which nothing in the
repo reads — the Discord flow is entirely client-side, with the webhook carried in the URL
fragment. It is left out of the blueprint rather than enshrined as dead config.

**Rate limiter and geolocation cache are per-process.** Both are module-level singletons,
so each gunicorn worker keeps its own. Effective rate limit is `configured x workers`, and
each worker warms its own geo cache. Fine at current scale; see issue #9.

## Invariants worth preserving

Each of these was a real bug. They are cheap to reintroduce.

- **Never `jsonify(*(body, status))`.** Splatting a `(dict, code)` tuple makes Flask
  serialize both as a JSON array and drop the status code, so errors return HTTP 200 with
  a nonsense body and the frontend renders a blank screen. Unpack first.
- **Never read the leftmost `X-Forwarded-For` entry.** Render's proxy appends without
  stripping what the client sent, so that entry is attacker-controlled. Use
  `get_client_ip()`, which prefers Cloudflare's `CF-Connecting-IP` and otherwise takes
  `remote_addr` as resolved by `ProxyFix` from the trusted tail. Tunable via
  `TRUSTED_PROXY_HOPS` and `TRUST_CF_CONNECTING_IP`.
- **Validate attack types against `FUMBLE_ATTACK_KEYS`.** Adding a fumble source requires
  an entry there; without one the roll fails cleanly rather than silently accepting
  arbitrary input. Only normalized values are echoed back into the response.
- **Chronicles narratives are text, not markup.** `modals.js` builds history rows with
  `textContent` and `append`. Reintroducing `innerHTML` there re-opens stored injection
  into every visitor's history, and the log is the one place user-influenced strings can
  persist.
- **Do not log raw request payloads.** `MAX_CONTENT_LENGTH` (16 KB) bounds the body, and
  the log stores only the rendered narrative plus a small structured record. Persisting
  the raw payload let any client write arbitrary bytes to disk.
- **Normalize before echoing or logging.** A padded `damageType` (`"fire"` plus
  whitespace) survives the table lookup because only the lookup is stripped. Echo the
  normalized key.

## Verifying a change

Worth running before pushing anything that touches roll logic:

- all four crit sources and three fumble sources return `status: success` with text
- a secondary roll (`rollContext: secondary`, type `minor`/`major`/`insanity`) resolves
- `/` returns 200 and the CSP hash still matches
- `/get_roll_history` returns entries with only `timestamp` and `narrative`
- guards hold: bad `attackType` errors, oversized body 413s, 21st roll in a minute 429s

When replacing something with a faster equivalent (as with the log tail reader), diff the
new implementation against the old across the real `narrative_dice_log.jsonl` plus empty,
blank-line, CRLF, no-trailing-newline, and multi-byte-boundary cases. That comparison
caught an off-by-one where a trailing newline consumed a slot and 49 entries came back
instead of 50.

## The Foundry module

`foundry/crits-fumbles/` is a Foundry VTT module for the `dnd5e` system, sharing this
repo's tables. It ships only the house tables and does not name them — it is the one
table set, so naming it added nothing.

### Build and release

```bash
python3 tools/build-foundry-tables.py        # app/*.json -> module data
./tools/package-foundry-module.sh            # build foundry/releases/
./tools/package-foundry-module.sh --release  # build, then publish a GitHub release
```

`data/tables.json` is **generated — never hand-edit it**. The converter normalizes the
two source shapes (crits are `{"1-15": "Title: Effect"}`, fumbles are
`[{roll, description, effect}]`) into one pre-parsed file, so the module's resolver is a
single `find()`. It refuses to write unless every table covers 1-100 with no gaps or
overlapping bands.

Installs come from a manifest URL, because the Foundry server is administered through
the web UI with no filesystem access:

```
https://github.com/adamwitwer/crits-fumbles/releases/latest/download/module.json
```

### Footguns

**A stale build is the most likely explanation for anything "missing".** Foundry serves
module scripts without cache-busting, so an ordinary refresh can keep running the
previous copy after an update — hard-reload with Cmd/Ctrl + Shift + R. The ready line
prints the version for exactly this reason, and `Object.keys(CritsFumbles)` shows what
the running build actually exposes. A missing API function and a missing setting that
shipped together are one symptom, not two.

**`raw.githubusercontent` branch URLs are CDN-cached.** They served the module while
GitHub's release API was down; a push took over two minutes to become installable. The
files stay in `foundry/releases/` so old installs keep resolving, but release assets are
the channel now. `--release` refuses to publish unless the manifest points at a
version-pinned release URL, so the two cannot be mixed up.

**`module.json` must be at the zip root.** Nesting it installs to
`Data/modules/crits-fumbles/crits-fumbles/` and fails silently. The packaging script
asserts this.

**dnd5e fires its roll hooks only on the client that made the roll**, not on every
client. A `game.user.isGM` guard on `dnd5e.rollAttack` therefore drops every player
attack — this was in the original design and was wrong. The rolling client does the
work; the one thing it cannot do is write the Combat flag behind the turn rule, so that
goes to a GM over the module socket (`"socket": true` in the manifest).

**The system often cannot tell you the damage type.** A monk's unarmed strike reports
`types: Set(2) {'bludgeoning', 'force'}` and the player picks per strike. Never infer it
— ask. Where damage *is* read, `includeBase: true` means the weapon's base damage is the
attack's primary type and `damage.parts` are riders on top, so base must outrank them or
a flame tongue rolls fire instead of slashing.

**`forceCrits` writes to the world database, not the browser.** It sets
`flags.dnd5e.weaponCriticalThreshold = 1` on the actor document, so it survives a
refresh, another browser and another machine — a character that "kept critting days
later" was this, not a bug. `clearForcedCrits()` sweeps for it, and clears **only the
value 1**: a Champion's Improved Critical uses the same flag with 19 or 18, and a
blunt sweep would break a real sheet. `tools/checks/forced-crits.mjs` guards that.

**Do not bind to `renderChatMessage`.** It was renamed in v13 (`renderChatMessageHTML`)
and its jQuery signature deprecated. The announcement card uses a delegated `document`
listener, which behaves the same across versions and survives re-renders.

**Foundry v14 and dnd5e 5.x are newer than the published docs**, so check the running
build rather than trusting a tutorial. Confirmed present on 14.366: `ApplicationV2`,
`DialogV2`, `HandlebarsApplicationMixin`,
`foundry.applications.handlebars.renderTemplate`, `game.keybindings`, `ui.controls`.
Dice So Nice is **not** installed, so cards must show the roll result themselves.
(`scripts/probe.js` reported all of this and was deleted once the UI was written
against it; `git show 3200af6:foundry/crits-fumbles/scripts/probe.js` if it is wanted
again.)

**Scene controls are a record, not an array, since v13.** Tools go to
`controls.tokens.tools.<name>` — `tokens` plural, `token` in v12 — and a `button: true`
tool **must** carry `onChange` or core throws on click (foundryvtt#12761). Do not
register a new control category: foundryvtt#12258 leaves its `activeTool` unset,
because core builds the tool list before `getSceneControlButtons` fires.

A tool's `title` is one localized string, so the headline tooltip is applied to the
rendered button in a `renderSceneControls` hook instead. **Set both
`data-tooltip-html` and `data-tooltip`**: v13 began treating `data-tooltip` as plain
text and added the `-html` variant for markup, and that split is unconfirmed on
14.366, so the plain attribute is the fallback rather than an oversight.
`CritsFumbles.checkTooltip()` reports which one the running build used. Do not warn
when the button is absent — tools render only for the open control group, so that is
the normal case.

**`HTMLElement` is not a global in every context this code loads in.** `element
instanceof HTMLElement` throws a ReferenceError under Node, and `instanceof
globalThis.HTMLElement` throws a TypeError when it is undefined. Duck-type instead:
`typeof element?.querySelector === "function"`.

**Take names from the system where it has them.** Damage type labels come from
`CONFIG.DND5E.damageTypes[key].label` and condition rule links from
`CONFIG.DND5E.conditionTypes[key].reference` — the latter resolved to
`Compendium.dnd5e.content24...` on 14.366, which no amount of guessing would have
produced. Only the three fumble categories are this module's own.

**All user-facing text lives in `lang/en.json`.** The render paths carry no English,
and `tools/check-foundry-module.mjs` fails if any creeps back in.

**Run the checks before shipping**, which `package-foundry-module.sh` does for you:

```bash
node tools/check-foundry-module.mjs
```

Eight suites over the module's pure logic, with a stub for `game` and `CONFIG`. They are
deliberately not full coverage — rendering, the socket handoff, and the dnd5e hook
signature itself can only be proved in a world. When reporting on a change, say which
side of that line it was verified on.

### Testing the module

Waiting for a natural 20 is a slow way to test. From the console:

```js
CritsFumbles.simulate({ kind: "crit" })      // full trigger path, real weapon, no dice
CritsFumbles.announceTest({ kind: "fumble" }) // post an announcement card directly
CritsFumbles.open()                           // the on-demand picker alone
CritsFumbles.forceCrits(true)                 // every attack crits, then (false)
CritsFumbles.turnStatus()                     // why the turn gate would allow or refuse
CritsFumbles.clearForcedCrits()               // find and undo every forceCrits left on
```

`simulate` works because only `total`, `isCritical` and `isFumble` are read off a roll,
so a plain object substitutes and everything downstream stays the production path.

Settings live under **Game Settings → Configure Settings → Module Settings**, not
Manage Modules. Turning off "Only the first attack of a turn can trigger" takes the
house rule out of the way while working on something else.

The logic that does not need Foundry is testable in Node by stubbing `fetch` and
`game`: `tables.js`, `damage-type.js` and `turn-gate.js` have no other globals. The turn
rule, damage-type extraction across dnd5e schema shapes, and fumble category resolution
are all covered that way, and every schema change so far was caught there first.
