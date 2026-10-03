# Reproduction

Source: `examples/system-design/labs/19/feed.py`

SHA256: `521b672cb5a8ccc118ee68cb16d005ad8a494fde3e2894c81f8e9f444b2c22b2`

Python 3.14.4; SQLite 3.51.3.

- `/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/labs/19/feed.py` → exit 0 (expected 0); output: [normal.stdout.txt](normal.stdout.txt); stderr: [normal.stderr.txt](normal.stderr.txt).
- `/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/labs/19/feed.py --unsafe` → exit 2 (expected 2); output: [unsafe.stdout.txt](unsafe.stdout.txt); stderr: [unsafe.stderr.txt](unsafe.stderr.txt).
- `/opt/homebrew/opt/python@3.14/bin/python3.14 -B examples/system-design/labs/19/feed.py --authority-down` → exit 3 (expected 3); output: [unavailable.stdout.txt](unavailable.stdout.txt); stderr: [unavailable.stderr.txt](unavailable.stderr.txt).

Only local teaching fixtures. Normal execution includes the failing-input assertions described in the source; no real payment, email, driver, or public website was contacted.
