# Reproduction

Source: `examples/system-design/labs/30/scheduler.py`

SHA256: `049486604a0e8e0a508e3273fb275ccf904b9d427a55b7480b27f4fc70d57af8`

Python 3.14.4; SQLite 3.51.3.

- `/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/labs/30/scheduler.py` → exit 0 (expected 0); output: [normal.stdout.txt](normal.stdout.txt); stderr: [normal.stderr.txt](normal.stderr.txt).

Only local teaching fixtures. Normal execution includes the failing-input assertions described in the source; no real payment, email, driver, or public website was contacted.

## Negative control

Remove one safeguard in an isolated source copy: stale owner bypasses completion fence.

`/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/evidence/30/negative-control.py` → exit 1 (expected assertion/constraint failure).

See [change](negative.diff), [source](negative-control.py), [stdout](negative.stdout.txt), [stderr](negative.stderr.txt), and [hash receipt](negative-verification.json). This deliberately broken copy is not the authoritative implementation.
