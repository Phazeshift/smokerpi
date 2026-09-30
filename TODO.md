# TODO

## Dependency migrations

Held back at the 2026-09 dependency update because each is a migration, not a bump.

- [ ] **React 18 → 19**: nothing blocks it any more (Router 7, Redux 5 / react-redux 9, Bootstrap 5 / react-bootstrap 2, recharts 3 all support 19, and `react-redux-toastr` is gone). Upgrade `react`, `react-dom` and `react-is`, then re-check `@testing-library/react` and re-test in a browser.

## Existing frontend issues

Found while browser-testing the dependency migrations (2026-09-30). None were introduced by them.

- [ ] **Config page shows a raw JSON dump**: `src/config.jsx` renders `<div>{text}</div>` (line ~60), where `text = JSON.stringify(this.state)`, above the form on every render. Looks like leftover debug output; remove it (keep the loading fallback if wanted).
- [ ] **"Push interval" field is bound to a key that doesn't exist**: `config.jsx` uses `push_interval`, but the backend config has no such key (the real one is `worker_interval`), so the input is always empty. Rename it to `worker_interval` or remove it, and check what saving does with the stray key.
- [ ] **Refreshing or deep-linking `/config` returns 404**: Flask only serves `/` and the static files (`api/smokerpi/__init__.py`), so a page refresh on a client-side route fails. Add a fallback that serves `index.html` for non-API, non-static paths.

## Verification

- [ ] Run the updated backend (Flask 3, Werkzeug 3, Adafruit stack) on a real Pi. Only emulated hardware has been tested. Confirm the Pi's Python is 3.9+.
