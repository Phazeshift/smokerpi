# TODO

## Dependency migrations

Held back at the 2026-09 dependency update because each is a migration, not a bump.

- [ ] **React 16 → 19** (via 18): required by the items below; also needs `@testing-library/react` 9 → 16 and `@testing-library/user-event` 7 → 14, `@testing-library/jest-dom` 4 → 7.
- [ ] **react-router 5 → 7** (via 6): then bump `react-router-bootstrap` 0.25 → 0.26 (0.26 needs Router 6 and crashes on 5: `useNavigate is not a function`).
- [ ] **Bootstrap / Bootswatch 4 → 5 and react-bootstrap 1 → 2**: do together; theme/CSS class changes throughout.
- [ ] **redux 4 → 5, react-redux 7 → 9, redux-thunk 2 → 3**: needs React 18+; redux-thunk 3 uses a named `thunk` export instead of the default import (`src/store.js`, `src/testUtils.js`, `src/App.test.js`, `src/actions/actions.test.js`).
- [ ] **recharts 1 → 3** (also lets us drop the `events` polyfill added in the Vite migration — recharts 1.x imports Node's `events`): 1.x is no longer maintained (prints a deprecation notice); API changes to `LineChart` usage.

## Verification

- [ ] Run the updated backend (Flask 3, Werkzeug 3, Adafruit stack) on a real Pi. Only emulated hardware has been tested. Confirm the Pi's Python is 3.9+.
