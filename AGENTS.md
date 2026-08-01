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

**`render.yaml` does not describe the deployed service.** It declares no disk and no
`LOG_STORAGE_DIR`, yet production clearly has persistent storage — the live Chronicles
returns entries spanning months across many deploys. Real config lives in the Render
dashboard. `app.py` falls back to `LOG_STORAGE_DIR=.` silently, so a service recreated
from this blueprint would look healthy while quietly resetting history on every deploy.
Tracked in issue #13.

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
