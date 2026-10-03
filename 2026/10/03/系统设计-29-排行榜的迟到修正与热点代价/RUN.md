# Reproduction

Source: `examples/system-design/labs/29/ranking.py`

SHA256: `8cd2b97b93a80f77f94ef65f7fc3a556fca69a1b3ff1714096aa3a772b04d1f9`

Python 3.14.4; SQLite 3.51.3.

- `/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/labs/29/ranking.py` → exit 0 (expected 0); output: [normal.stdout.txt](normal.stdout.txt); stderr: [normal.stderr.txt](normal.stderr.txt).

Only local teaching fixtures. Normal execution includes the failing-input assertions described in the source; no real payment, email, driver, or public website was contacted.

## Negative control

Remove one safeguard in an isolated source copy: duplicate score counted twice.

`/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/evidence/29/negative-control.py` → exit 1 (expected assertion/constraint failure).

See [change](negative.diff), [source](negative-control.py), [stdout](negative.stdout.txt), [stderr](negative.stderr.txt), and [hash receipt](negative-verification.json). This deliberately broken copy is not the authoritative implementation.
