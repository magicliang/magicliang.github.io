# Reproduction

Source: `examples/system-design/labs/23/crawler.py`

SHA256: `75b20802585322e8147ae88bbc75d65197854f824f318a2f0c989ede9ffa8443`

Python 3.14.4; SQLite 3.51.3.

- `/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/labs/23/crawler.py` → exit 0 (expected 0); output: [normal.stdout.txt](normal.stdout.txt); stderr: [normal.stderr.txt](normal.stderr.txt).

Only local teaching fixtures. Normal execution includes the failing-input assertions described in the source; no real payment, email, driver, or public website was contacted.

## Negative control

Remove one safeguard in an isolated source copy: robots prohibition ignored.

`/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/evidence/23/negative-control.py` → exit 1 (expected assertion/constraint failure).

See [change](negative.diff), [source](negative-control.py), [stdout](negative.stdout.txt), [stderr](negative.stderr.txt), and [hash receipt](negative-verification.json). This deliberately broken copy is not the authoritative implementation.
