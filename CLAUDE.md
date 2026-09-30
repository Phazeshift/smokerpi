# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SmokerPi: a Raspberry Pi app that controls a BBQ smoker's blower/damper via a PID loop and reports temperature. It's two apps in one repo, meant to be deployed together on the Pi:

- `src/` — React 19 + Redux frontend (built with Vite, tested with Vitest).
- `api/` — Flask backend (`api/smokerpi/`) that drives the hardware and serves the built frontend as static files.

On the real Pi (Linux), the backend talks to actual GPIO/SPI/pigpio hardware. Everywhere else (Windows/macOS dev machines, Linux CI), it runs against emulated hardware automatically — see "Hardware emulation" below. This is what makes the backend testable off-Pi at all.

## Commands

### Frontend (run from repo root)
- Install: `yarn install`
- Dev server: `yarn start` (Vite; proxies `/api` and `/socket.io` to the Flask backend on `localhost:5000`).
- Tests: `yarn test` (Vitest, watch mode; `yarn vitest run` for a single run, as CI does). Single file: `yarn vitest run src/controls.test.jsx`.
- Build: `yarn build` — outputs to `build/` (set in `vite.config.mjs`) because Flask serves `../../build` and the release workflow packages it.

### Backend (run from `api/`)
- Install: `pip install -r requirements.txt -r requirements-dev.txt` (the `-dev` file layers `pytest`/`pytest-cov` on top).
- Tests: `pytest -v`. Single test: `pytest tests/test_api.py::TestBlowerEndpoint::test_enabling_turns_blower_on`.
- Off-Pi and not on Windows (e.g. a Linux shell), set `SMOKERPI_TEST=1` first so the app uses emulated hardware instead of trying to talk to real GPIO/pigpio.
- Run the server for real: `yarn start-api` from repo root (activates `api/venv` and runs `api/runserver.py`), or `yarn start-api2` for `flask run`.

CI (`.github/workflows/ci.yml`, Node 22 — Vitest requires 22.12+) runs both suites plus a frontend build on every push/PR to `master`, including Dependabot PRs — treat a red CI run on a dependency bump as a real finding, not a fluke (see `api/requirements.txt`'s history for two examples where a Dependabot-proposed bump was incompatible with other pinned packages and CI was what caught it).

## Deployment

`build/` is gitignored — it is not committed. Pushing a tag like `v1.2.3` runs `.github/workflows/release.yml`, which builds the frontend and publishes a GitHub Release containing `smokerpi.tar.gz` (built frontend + `api/smokerpi`, `runserver.py`, `requirements.txt`, the shell scripts, and a `VERSION` file). On the Pi, `sudo ./update.sh` finds the latest release, installs it over the current directory, runs `pip install` only if `requirements.txt` changed, and restarts the `smokerpiboot` init service. It preserves `api/config.json` and `api/venv`. Tag only commits that have passed CI on `master`.

`runserver.sh` uses `exec python ...` on purpose: the init script's PID file must track python itself or a service restart leaves the old server holding the port. Shell scripts are pinned to LF via `.gitattributes`.

## Architecture

### Backend: app factory + module-level hardware setup

`api/smokerpi/__init__.py` exposes `create_app(test_config=None)`. `test_config` (a dict with optional `config` and `start_worker` keys) lets callers — namely `api/tests/conftest.py` — inject a config dict directly (skipping real `config.json` I/O) and skip starting the background worker thread. A module-level `app = create_app()` at the bottom of the file exists only so `api/runserver.py`'s `from smokerpi import app, cleanupHardware` keeps working for real production startup.

Flask serves the built frontend from `../../build`. Because the React app does its own routing, a NotFound handler in `create_app()` returns `index.html` for unknown GET/HEAD paths that are not under `/api/` and have no file extension (so refreshing or deep-linking `/config` works); API paths and missing files stay real 404s, and with no build present everything stays 404. `api/tests/test_static.py` covers this against a temp static folder, so it needs no frontend build.

Inside `create_app()`, `setup()` runs synchronously: it loads config (`Config` in `config.py`), constructs the hardware objects (`configure()`), and spawns a daemon thread (`worker()`) that polls temperature, feeds it through a `simple_pid.PID` controller, and appends to an in-memory graph-data list every `graph_interval` seconds. All live state (current temperature, graph data, hardware objects, the PID object) is stored directly as attributes on the Flask `app` object (`app.smokerpi_*`), not in a separate model/service layer — routes and the worker loop both read/write these attributes directly.

### Hardware emulation

Test/emulated mode is selected once, in `create_app()`: `app.smokerpi_test = platform.system() == 'Windows' or os.environ.get('SMOKERPI_TEST') == '1'`. This flag decides, per-device, which implementation `configure()` wires up:
- Damper: real `Damper` (talks to `pigpio`) vs. `TestDamper` (in-memory) — both in `hardware/damper2.py`.
- Thermocouple: real `MAX31855` (bit-banged SPI reads) vs. `TestMAX31855`, which synthesizes a temperature that drifts toward the pit controller's current output (`hardware/max31855.py`).
- Blower (`hardware/blower.py`) has no separate test class — it always talks to `RPi.GPIO`, which resolves to the real driver on a Pi or falls back to a hand-rolled no-op shim at `hardware/RPi/GPIO.py` everywhere else (that fallback is itself the emulation, not something tests set up).

`hardware/damper.py` (singular) is legacy/dead code using the Adafruit CircuitPython stack — nothing imports it; `hardware/__init__.py` is empty. Don't confuse it with the actually-used `damper2.py`.

### Config persistence

`api/smokerpi/config.py`'s `Config` class reads/writes `api/config.json` (gitignored, not present on a fresh checkout — `defaultConfig()` supplies fallback values that get merged with whatever's on disk and written back). In test mode it also scales `worker_interval`/`graph_interval` down 10x (`applyTestConfig`) so the emulated worker loop runs fast, but `saveConfig()` never rewrites the intervals: it saves a *copy* of the config it is given (the API passes the live dict, which must not change) and keeps whatever `worker_interval`/`graph_interval` are already on disk, falling back to the defaults. So scaled test values never leak into the persisted file, and hand-edited intervals survive a save.

`POST /api/config` only accepts the four editable settings (`EDITABLE_FIELDS` in `config.py`: `set_temperature`, `blower_minimum`, `damper_minimum`, `damper_maximum`), checked by `validateEditableConfig()` — whole numbers (numeric strings are fine, the form sends strings), blower 0–100, damper 500–2500 with min < max. Anything invalid is a 400 with `{"error": "...", "errors": {field: message}}`; the frontend shows `error` in the banner. Pins and intervals are read-only over the API (they need a restart), which is why the Config page shows them disabled; change them in `config.json`.

### Frontend: Redux shape and API access

There's a single combined reducer mounted under the `smokerpi` key (`rootReducer.js` → `reducers/reducer.js`), holding `{ graphData, graphIndex, config, state }` plus an optional `error`. All server access goes through thunk action creators in `actions/actions.js` (`getConfig`, `updateConfig`, `getCurrentState`, `toggleBlower`, `toggleDamper`, `toggleAutomatic`, `getGraphData`), which call the two small `api`/`postApi` helpers wrapping `fetch`. Note `postApi`'s success callback fires an unawaited follow-up dispatch (e.g. `updateConfig` posts, then dispatches `getConfig()` to refresh state) — the POST's own promise resolves before that follow-up fetch completes, which matters if you're writing a test around it (see the `flushPromises` helper in `actions.test.js`).

Failed API calls dispatch `API_ERROR` (with a message); `errorbanner.jsx`, rendered once in `App`, shows it as a dismissible alert until it is dismissed (`API_ERROR_DISMISSED`) or any later `LOAD_*_SUCCESS` action arrives (the reducer drops `error` on those). There is no toast library.

`socketMiddleware.js` opens a `socket.io-client` connection and bridges it into Redux: incoming `message` events dispatch `SOCKET_MESSAGE_RECEIVED` (merged into state by the reducer), and actions of type `SEND_WEBSOCKET_MESSAGE` are intercepted and emitted over the socket instead of being passed down the middleware chain.

### Testing conventions

- Backend tests (`api/tests/`) use the `app`/`client` fixtures from `conftest.py`, which always build via `create_app(test_config=...)` — never rely on the module-level `app` singleton in a test, since that one starts a real worker thread. Anything touching `Config`'s disk I/O (loading/saving `config.json`) needs `monkeypatch.chdir(tmp_path)` first so it doesn't clobber the real (gitignored) `api/config.json`.
- Frontend component tests use `renderWithStore` (`src/testUtils.jsx`) to wrap a component in a real Redux store + `Provider`; `fetch` is globally mocked via `vitest-fetch-mock` (wired up in `src/setupTests.js`), so give it a `mockResponse`/`mockResponseOnce` before rendering anything that fetches on mount.

### Known encoding/platform traps

- `api/requirements.txt` is UTF-8-with-BOM (not plain UTF-8, not UTF-16 — it's been both at different points in this repo's history after tooling round-trips). If you edit it, verify the byte-level encoding survived (`open(path, 'rb').read()[:5]` should start `\xef\xbb\xbf`) before committing — a naive text edit through a tool that assumes ASCII/UTF-8-without-BOM can silently corrupt it, and Git will refuse to line-merge it (reports "Cannot merge binary files") if two branches touch it with different encodings.
- Files containing JSX must use the `.jsx` extension (Vite does not parse JSX in `.js`). Imports must match filename casing exactly — Windows/macOS filesystems are case-insensitive so a wrong-case import (e.g. `./app` for `App.js`) works locally and only breaks the production build on Linux (this happened for real; see `src/index.js`'s git history).
- React 19 ignores `defaultProps` and `propTypes` on function components; use default parameter values. Class components under `connect` get a fresh props object on every render (react-redux passes a `ref` prop, which React 19 strips by copying), so never compare `prevProps !== this.props` in `componentDidUpdate` — compare the prop values (see `config.jsx`), or it loops forever.
