# TODO

## Dependency migrations

Held back at the 2026-09 dependency update because each is a migration, not a bump.

- [ ] **React 18 → 19**: React 18 is done. 19 is blocked by libraries whose React peer range stops at 18 or earlier: `react-redux` 7 (needs 9, see the Redux item), `react-redux-toastr` 7 (supports up to 18), `recharts` 1 (officially React 16 only; needs 3), and `react-bootstrap` 1 (needs 2 for 19). Do this after those three items.
- [ ] **Bootstrap / Bootswatch 4 → 5 and react-bootstrap 1 → 2**: do together; theme/CSS class changes throughout.
- [ ] **redux 4 → 5, react-redux 7 → 9, redux-thunk 2 → 3**: needs React 18+; redux-thunk 3 uses a named `thunk` export instead of the default import (`src/store.js`, `src/testUtils.js`, `src/App.test.js`, `src/actions/actions.test.js`).
- [ ] **recharts 1 → 3** (also lets us drop the `events` polyfill added in the Vite migration — recharts 1.x imports Node's `events`): 1.x is no longer maintained (prints a deprecation notice); API changes to `LineChart` usage.

## Existing frontend issues

Found while checking the Vite migration in a real browser (2026-09-30). None were introduced by it.

- [ ] **Config page shows a raw JSON dump**: `src/config.jsx` renders `<div>{text}</div>` (line ~60), where `text = JSON.stringify(this.state)`, above the form on every render. Looks like leftover debug output; remove it (keep the loading fallback if wanted).
- [ ] **"Push interval" field is bound to a key that doesn't exist**: `config.jsx` uses `push_interval`, but the backend config has no such key (the real one is `worker_interval`), so the input is always empty. Rename it to `worker_interval` or remove it, and check what saving does with the stray key.
- [ ] **Refreshing or deep-linking `/config` returns 404**: Flask only serves `/` and the static files (`api/smokerpi/__init__.py`), so a page refresh on a client-side route fails. Add a fallback that serves `index.html` for non-API, non-static paths.

## Verification

- [ ] Run the updated backend (Flask 3, Werkzeug 3, Adafruit stack) on a real Pi. Only emulated hardware has been tested. Confirm the Pi's Python is 3.9+.
