# TODO

## Dependency migrations

Held back at the 2026-09 dependency update because each is a migration, not a bump.

- [ ] **React 18 → 19**: React 18 is done, as are Router 7, Redux 5 / react-redux 9, Bootstrap 5 / react-bootstrap 2 and recharts 3. The only remaining blocker is `react-redux-toastr` 8, which supports React up to 18. Resolve it by dropping the library (see the toast item below; it is effectively unused, since `<ReduxToastr />` is never mounted) or finding a replacement, then upgrade React, `react-dom` and `react-is` and re-check `@testing-library/react`.

## Existing frontend issues

Found while browser-testing the dependency migrations (2026-09-30). None were introduced by them.

- [ ] **Config page shows a raw JSON dump**: `src/config.jsx` renders `<div>{text}</div>` (line ~60), where `text = JSON.stringify(this.state)`, above the form on every render. Looks like leftover debug output; remove it (keep the loading fallback if wanted).
- [ ] **"Push interval" field is bound to a key that doesn't exist**: `config.jsx` uses `push_interval`, but the backend config has no such key (the real one is `worker_interval`), so the input is always empty. Rename it to `worker_interval` or remove it, and check what saving does with the stray key.
- [ ] **API error toasts never appear**: `src/actions/actions.js` calls `toastr.error(...)` on failed requests, but `<ReduxToastr />` is never mounted and the toastr reducer isn't in the store, so failures are silent (checked in a browser with the API down: no toast, no error text). Either mount `ReduxToastr` (plus its reducer and CSS) or replace the library with a simple inline error message; replacing it would also remove a React 19 blocker.
- [ ] **Refreshing or deep-linking `/config` returns 404**: Flask only serves `/` and the static files (`api/smokerpi/__init__.py`), so a page refresh on a client-side route fails. Add a fallback that serves `index.html` for non-API, non-static paths.

## Verification

- [ ] Run the updated backend (Flask 3, Werkzeug 3, Adafruit stack) on a real Pi. Only emulated hardware has been tested. Confirm the Pi's Python is 3.9+.
