# Reproduction

Source: `examples/system-design/labs/26/tickets.py`

SHA256: `26e369415000c7918fccc1481b2dff725ea60f037f13dc9b86b33ba9d9be12be`

Python 3.14.4; SQLite 3.51.3.

- `/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/labs/26/tickets.py` → exit 0 (expected 0); output: [normal.stdout.txt](normal.stdout.txt); stderr: [normal.stderr.txt](normal.stderr.txt).

Only local teaching fixtures. Normal execution includes the failing-input assertions described in the source; no real payment, email, driver, or public website was contacted.

## Negative control

Remove one safeguard in an isolated source copy: different event ID regresses paid terminal state.

`/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/evidence/26/negative-control.py` → exit 1 (expected assertion/constraint failure).

See [change](negative.diff), [source](negative-control.py), [stdout](negative.stdout.txt), [stderr](negative.stderr.txt), and [hash receipt](negative-verification.json). This deliberately broken copy is not the authoritative implementation.
