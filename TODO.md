# TODO

## Dependency migrations

All planned migrations are done (2026-09-30): Vite/Vitest, React 19, Router 7, Redux 5, Bootstrap 5, recharts 3.

## Existing frontend issues

Found while browser-testing the dependency migrations (2026-09-30). None were introduced by them.

- [ ] **Config page shows a raw JSON dump**: `src/config.jsx` renders `<div>{text}</div>` (line ~60), where `text = JSON.stringify(this.state)`, above the form on every render. Looks like leftover debug output; remove it (keep the loading fallback if wanted).
- [ ] **"Push interval" field is bound to a key that doesn't exist**: `config.jsx` uses `push_interval`, but the backend config has no such key (the real one is `worker_interval`), so the input is always empty. Rename it to `worker_interval` or remove it, and check what saving does with the stray key.
- [ ] **Refreshing or deep-linking `/config` returns 404**: Flask only serves `/` and the static files (`api/smokerpi/__init__.py`), so a page refresh on a client-side route fails. Add a fallback that serves `index.html` for non-API, non-static paths.

## Verification

- [ ] Run the updated backend (Flask 3, Werkzeug 3, Adafruit stack) on a real Pi. Only emulated hardware has been tested. Confirm the Pi's Python is 3.9+.
