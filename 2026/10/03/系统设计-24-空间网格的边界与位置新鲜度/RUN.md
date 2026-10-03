# Reproduction

Source: `examples/system-design/labs/24/nearby.py`

SHA256: `408097b65d490c1122a7d0c22cef3de964487ea816bf68d49cc3e3e3d518c042`

Python 3.14.4; SQLite 3.51.3.

- `/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/labs/24/nearby.py` → exit 0 (expected 0); output: [normal.stdout.txt](normal.stdout.txt); stderr: [normal.stderr.txt](normal.stderr.txt).

Only local teaching fixtures. Normal execution includes the failing-input assertions described in the source; no real payment, email, driver, or public website was contacted.

## Negative control

Remove one safeguard in an isolated source copy: center-cell-only misses boundary.

`/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/evidence/24/negative-control.py` → exit 1 (expected assertion/constraint failure).

See [change](negative.diff), [source](negative-control.py), [stdout](negative.stdout.txt), [stderr](negative.stderr.txt), and [hash receipt](negative-verification.json). This deliberately broken copy is not the authoritative implementation.
