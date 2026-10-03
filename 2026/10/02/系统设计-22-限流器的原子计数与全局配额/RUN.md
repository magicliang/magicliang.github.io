# Reproduction

Source: `examples/system-design/labs/22/limiter.py`

SHA256: `b087b1af103c2b7d3d98f7a9af9d81fe091e24f6ea6d8a97221330237b8f803f`

Python 3.14.4; SQLite 3.51.3.

- `/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/labs/22/limiter.py` → exit 0 (expected 0); output: [normal.stdout.txt](normal.stdout.txt); stderr: [normal.stderr.txt](normal.stderr.txt).

Only local teaching fixtures. Normal execution includes the failing-input assertions described in the source; no real payment, email, driver, or public website was contacted.

## Negative control

Remove one safeguard in an isolated source copy: storage error allowed through take.

`/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/evidence/22/negative-control.py` → exit 1 (expected assertion/constraint failure).

See [change](negative.diff), [source](negative-control.py), [stdout](negative.stdout.txt), [stderr](negative.stderr.txt), and [hash receipt](negative-verification.json). This deliberately broken copy is not the authoritative implementation.
