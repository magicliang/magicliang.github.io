# Reproduction

Source: `examples/system-design/labs/28/payment.py`

SHA256: `39f0f5b18b4a7c98f160a53a908d45ab6e8739ffacc7b412d2269de0c7e3af08`

Python 3.14.4; SQLite 3.51.3.

- `/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/labs/28/payment.py` → exit 0 (expected 0); output: [normal.stdout.txt](normal.stdout.txt); stderr: [normal.stderr.txt](normal.stderr.txt).

Only local teaching fixtures. Normal execution includes the failing-input assertions described in the source; no real payment, email, driver, or public website was contacted.

## Negative control

Remove one safeguard in an isolated source copy: lost-reply retry uses new charge key.

`/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/evidence/28/negative-control.py` → exit 1 (expected assertion/constraint failure).

See [change](negative.diff), [source](negative-control.py), [stdout](negative.stdout.txt), [stderr](negative.stderr.txt), and [hash receipt](negative-verification.json). This deliberately broken copy is not the authoritative implementation.
