# TODO

## Dependency migrations

All planned migrations are done (2026-09-30): Vite/Vitest, React 19, Router 7, Redux 5, Bootstrap 5, recharts 3.

## Existing issues

Found while browser-testing the dependency migrations (2026-09-30). None were introduced by them.

- [ ] **Most of the Config form doesn't do anything.** `POST /api/config` (`api/smokerpi/__init__.py`) only applies `set_temperature`, `blower_minimum`, `damper_minimum` and `damper_maximum`. The three pin fields (CS/clock/data), both blower pins, the damper pin and "Graph interval" are accepted and silently ignored (verified: posting `cs_pin: 5, graph_interval: 99` returns the old values). Decide whether to make them read-only in the UI (they need a restart to take effect anyway) or apply them.
- [ ] **Bad input to `POST /api/config` crashes with a bare 500.** The handler does `int(request.json[...])` with no validation, so a blank or non-numeric value raises `ValueError`, and `handle_500` then fails itself with `AttributeError: 'InternalServerError' object has no attribute 'message'` (verified). The UI now shows this as "Error calling api: INTERNAL SERVER ERROR". Validate input (return 400 with a message the banner can show) and fix `handle_500` to use `e.description`. Also drop the leftover `print(request.json)`.
- [ ] **`Config.saveConfig` overwrites the intervals and mutates live state** (from reading the code, not reproduced): it sets `worker_interval` and `graph_interval` to the defaults *on the dict passed in*, which is the live `app.smokerpi_config`. So saving from the UI would reset a hand-edited interval in `config.json` and changes the running config. It exists to undo test-mode scaling; do that on a copy instead.
- [ ] **Phone layout: the fixed navbar overlaps the top of the page.** Below the `lg` breakpoint the expanded/collapsed navbar covers the top of the status card (`body { padding-top: 80px }` in `src/App.css` is a fixed guess). Seen in the before/after screenshots; long-standing.

## Verification

- [ ] Run the updated backend (Flask 3, Werkzeug 3, Adafruit stack) on a real Pi. Only emulated hardware has been tested. Confirm the Pi's Python is 3.9+.
