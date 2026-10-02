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
- Dev server: `yarn start` (Vite; proxies `/api` to the Flask backend on `localhost:5000`).
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

Production must never run in debug mode. Flask 2.0's `app.run()` loads `.flaskenv` itself and, if that sets `FLASK_ENV`, re-enables debug over `app.debug = False`, which exposed the interactive Werkzeug debugger (`/console`) on the Pi's LAN address. So `runserver.py` passes `debug=False, load_dotenv=False` explicitly and `api/.flaskenv` holds only `FLASK_APP`; `api/tests/test_deployment.py` guards both. `.flaskenv` stays in the bundle on purpose: an already-installed `update.sh` copies it unconditionally, so omitting it would abort an update after the old code was deleted. The installed `update.sh` is always the *previous* release's copy, so keep any change to what the bundle contains compatible with older `update.sh` versions.

`update.sh` replaces itself while bash is still reading it, which is easy to get wrong: bash reads a script incrementally, so overwriting it in place makes bash resume at a stale byte offset in the *new* text and execute whatever fragment lands there (v0.3.0 and v0.3.1 shipped this bug: "syntax error near unexpected token" after the update had already been applied). So `update.sh` replaces itself by `mv`-ing a new file over it (the running bash keeps the old inode), and ends with `main "$@"; exit $?` on ONE line so nothing is left to read. Do not undo either. Because the copy doing the work is always the *previous* release's, `api/tests/test_update_script.py` also runs frozen copies of the earlier releases' scripts (`api/tests/fixtures/`) against the current one and checks the update is intact; when you cut a release that changes `update.sh`, add the outgoing version to the fixtures. Those tests run `update.sh` for real in a scratch install with a fake `curl`; they need bash and skip on Windows unless `SMOKERPI_SCRIPT_TESTS=1` (Git Bash), and CI runs them on Linux.

The Pi needs Python 3.9+ (the pins are Flask 3 / Werkzeug 3). `install.sh` checks this up front, and `update.sh` checks the venv's Python before running pip when `requirements.txt` changed, aborting before anything is touched.

`runserver.sh` uses `exec python ...` on purpose: the init script's PID file must track python itself or a service restart leaves the old server holding the port. Shell scripts are pinned to LF via `.gitattributes`.

## Architecture

### Backend: app factory

`api/smokerpi/__init__.py` exposes `create_app(test_config=None)`. `test_config` (a dict with optional `config` and `start_worker` keys) lets callers — namely `api/tests/conftest.py` — inject a config dict directly (skipping real `config.json` I/O) and skip starting the background worker thread. Importing `smokerpi` (or any submodule) has no side effects: there is deliberately no module-level `app`, because one used to be created at import, which read and wrote `config.json`, created `log/` and started a live worker thread in every test process (and made the worker write into whichever directory the tests were in). `api/runserver.py`'s `main()` calls `create_app()` and wires `app.cleanupHardware` to SIGTERM/SIGINT; `flask run` (`FLASK_APP=smokerpi`) finds the `create_app` factory itself. `api/tests/test_no_import_side_effects.py` guards all of this in a clean interpreter.

Flask serves the built frontend from `../../build`. Because the React app does its own routing, a NotFound handler in `routes.py` returns `index.html` for unknown GET/HEAD paths that are not under `/api/` and have no file extension (so refreshing or deep-linking `/config` works); API paths and missing files stay real 404s, and with no build present everything stays 404. `api/tests/test_static.py` covers this against a temp static folder, so it needs no frontend build.

Inside `create_app()`, `setup()` runs synchronously: it loads config (`Config` in `config.py`), constructs the hardware objects (`configure()`), and spawns a daemon thread (`worker()`) that polls temperature, feeds it through a `simple_pid.PID` controller, and appends to an in-memory graph-data list every `graph_interval` seconds. All live state (current temperature, graph data, hardware objects, the PID object) is stored directly as attributes on the Flask `app` object (`app.smokerpi_*`), not in a separate model/service layer — routes and the worker loop both read/write these attributes directly.

`create_app()` only wires things up; the code lives in modules next to it: `routes.py` (`registerRoutes`: every route, the SPA NotFound fallback and the 500 logger), `auth.py` (`registerAuth`: the password hook), `worker.py` (the `Worker` class: the control loop and `error()` for the watchdog) and `config.py` (`applyConfig(app)`, which pushes the setpoint, gains and damper settings onto the live objects, at startup and after a POST). The live state stays on the `app` (`app.smokerpi_*`), not on the `Worker`.

The worker loop must never die: each pass is `Worker.step()` (exposed as `app.smokerpi_workerStep` for tests), which runs the temperature read, PID update and graph update through `runStep()`, logs any exception with a traceback and carries on. If the temperature read or PID/hardware step fails it **fails safe by switching the blower off** (and skips the PID for that pass rather than act on a reading it could not take); a graph failure is only logged. Previously any exception killed the thread silently, freezing the temperature and PID while leaving the blower in whatever state it was in. The thermocouple sometimes misses a read and answers the next, so a failed read (any exception, `MAX31855Error` included) is only logged as a warning and the last good temperature is kept; the step counts as failed, and fails safe, once no read has succeeded for `sensor_timeout` seconds (default 60, read-only over the API; `app.smokerpi_clock`/`smokerpi_lastReading` let tests move time). The first good read after that resumes control. `/api/state` carries `workerError` (null when healthy): the failed steps with their messages, or "Control loop has stopped" if no pass has completed for max(30s, 3x worker_interval) (the watchdog, which also catches a dead or hung worker thread); `StatusCard` shows it as an alert. It is a separate alert, not the error banner, because the banner clears on any successful load.

### Hardware emulation

Test/emulated mode is selected once, in `create_app()`: `app.smokerpi_test = platform.system() == 'Windows' or os.environ.get('SMOKERPI_TEST') == '1'`. This flag decides, per-device, which implementation `configure()` wires up:
- Damper: real `Damper` (talks to `pigpio`) vs. `TestDamper` (in-memory) — both in `hardware/damper2.py`.
- Thermocouple: real `MAX31855` (bit-banged SPI reads) vs. `TestMAX31855`, which synthesizes a temperature that drifts toward the pit controller's current output (`hardware/max31855.py`).
- Blower (`hardware/blower.py`) has no separate test class — it always talks to `RPi.GPIO`, which resolves to the real driver on a Pi or falls back to a hand-rolled no-op shim at `hardware/RPi/GPIO.py` everywhere else (that fallback is itself the emulation, not something tests set up). **The shim accepts any call**, so a hardware-protocol mistake (e.g. writing to a pin that was never `GPIO.setup(..., OUT)`, which real `RPi.GPIO` rejects with a RuntimeError) passes CI and only fails on the Pi; that is exactly how the blower button returned 500 after a one-line change to `pwmMode`. `tests/test_blower.py` therefore also runs the Blower against a `StrictGPIO` that enforces the real library's rules; do the same for any new hardware code.

`hardware/__init__.py` is empty. The servo driver is `damper2.py`; the `2` is left over from an older Adafruit-based `damper.py`, which has been removed.

### PID

`app.smokerpi_pid` is an `AntiWindupPID` (`api/smokerpi/pid.py`, a `simple_pid.PID` subclass): the integral is rolled back in any step that leaves the output saturated in the direction of the error, which plain `simple_pid` does not do (it only clamps the integral to the output range). Gains come from `pid_kp`/`pid_ki`/`pid_kd` in config: applied by `applyConfig()` at startup, and editable over `POST /api/config` (optional `gain` fields in `FIELDS` in `config.py`: floats from 0 to 100/10/100; applied live by setting `pid.tunings`) and on the Config page, which only shows them if the server sends them. The blower only turns on above output 99, which with the default Kp of 1 used to be reached through windup alone; see TODO.md before changing the gains or that threshold.

### History

`api/smokerpi/history.py` (`History`) appends every graph point to `data/history.csv` (`data/` next to `config.json` and `log/`, fixed to an absolute path when the app is created because the worker thread keeps writing for the life of the process; `update.sh` only removes `build` and `api/smokerpi`, so `api/data` survives, and `test_update_script.py` checks it). Each row carries the graph point number (`point`), and at startup `setup()` loads the newest `GRAPH_POINTS` (2000) back into `app.smokerpi_graphData` with those numbers and carries on from the last one, so the graph survives a restart and a browser tab left open across one (which polls `/api/graph?from=<its last number>`) keeps getting new points. The file is trimmed to about half of `history_max_mb` (default 5) whenever it passes it, via a temp file and `os.replace`; damaged lines (a power loss mid-write) are skipped and a half-written last line is terminated before the next append. `History` never raises: errors are logged, so a disk problem cannot reach the control loop (`graphData()` appends to the in-memory list first). `GET /api/history.csv` serves the file (behind the password like everything else). Known limit: deleting `data/history.csv` while the app is running restarts the numbering at the next restart, which strands an open tab until its number is passed.
### Damper direction

`damper_invert` (default false) mirrors the position onto the pulse range inside `Damper.open()` (`value` becomes `100 - value` before mapping); the logical position, `state`, the PID and the UI still mean 100 = open. It is an optional boolean in `POST /api/config`, applied live, and a change calls `Damper.reposition()` so the servo moves to the mirrored position (the PID would not re-send an unchanged value). If that move fails the setting is kept, `state` is left at -1 so the next move is sent, and the POST is a 500 saying so.

### Password

`password` in `config.json` (default empty = off, so an update never locks the owner out; the startup log warns when it is off) turns on HTTP Basic auth for every request via a `before_request` hook in `auth.py`: any username, constant-time comparison. It covers the static frontend and unknown paths too. `publicConfig()` strips it from every API response and it has no editable `kind` in `FIELDS`. The control endpoints validate `enabled` (must be a JSON boolean, else 400) before touching the PID or hardware. `api/tests/test_auth.py` covers it.

### Config persistence

`api/smokerpi/config.py`'s `Config` class reads/writes `api/config.json` (gitignored, not present on a fresh checkout — `defaultConfig()` supplies fallback values that get merged with whatever's on disk and written back). In test mode it also scales `worker_interval`/`graph_interval` down 10x (`applyTestConfig`) so the emulated worker loop runs fast, but `saveConfig()` never rewrites the intervals: it saves a *copy* of the config it is given (the API passes the live dict, which must not change) and keeps whatever `worker_interval`/`graph_interval` are already on disk, falling back to the defaults. So scaled test values never leak into the persisted file, and hand-edited intervals survive a save.

`POST /api/config` only accepts the three required settings (`whole` fields in `FIELDS` in `config.py`, which is also where every default lives, plus the label and help text the Config page shows: `set_temperature`, `damper_minimum`, `damper_maximum`), checked by `validateEditableConfig()` — whole numbers (numeric strings are fine, the form sends strings), damper 500–2500 with min < max. Anything invalid is a 400 with `{"error": "...", "errors": {field: message}}`; the frontend shows `error` in the banner. `GET`/`POST /api/config` also return `fields` (`describeFields()`: name, label, kind, help of each labelled setting present in the config), and the Config page builds its form from that list, so adding a setting means adding a `Field` and nothing in the frontend; a field with no label (the password, intervals not meant for display) or a key with no `Field` (a stale `blower_minimum`) is never sent or shown, and the page never posts `fields` back. Pins and intervals are read-only over the API (they need a restart), which is why the Config page shows them disabled; change them in `config.json`. There used to be a `blower_minimum` setting; the control loop stopped reading it when the damper was added (the blower is now simply on above PID output 99), so it was removed. A leftover `blower_minimum` in an old `config.json` is harmless and ignored.

### Frontend: Redux shape and API access

There's a single combined reducer mounted under the `smokerpi` key (`rootReducer.js` → `reducers/reducer.js`), holding `{ graphData, graphIndex, config, state }` plus an optional `error`. All server access goes through thunk action creators in `actions/actions.js` (`getConfig`, `updateConfig`, `getCurrentState`, `toggleBlower`, `toggleDamper`, `toggleAutomatic`, `getGraphData`), which call the two small `api`/`postApi` helpers (both built on one `request` helper wrapping `fetch`). Note `postApi`'s success callback fires an unawaited follow-up dispatch (e.g. `updateConfig` posts, then dispatches `getConfig()` to refresh state) — the POST's own promise resolves before that follow-up fetch completes, which matters if you're writing a test around it (see the `flushPromises` helper in `actions.test.js`).

Failed API calls dispatch `API_ERROR` (with a message); `errorbanner.jsx`, rendered once in `App`, shows it as a dismissible alert until it is dismissed (`API_ERROR_DISMISSED`) or any later `LOAD_*_SUCCESS` action arrives (the reducer drops `error` on those). There is no toast library.

### Testing conventions

- Backend tests (`api/tests/`) use the `app`/`client` fixtures from `conftest.py`, which always build via `create_app(test_config=...)` — there is no module-level app to rely on, and a worker thread only runs if a test starts one on purpose. An autouse fixture runs every test in a temp directory. Anything touching `Config`'s disk I/O (loading/saving `config.json`) needs `monkeypatch.chdir(tmp_path)` first so it doesn't clobber the real (gitignored) `api/config.json`.
- Frontend component tests use `renderWithStore` (`src/testUtils.jsx`) to wrap a component in a real Redux store + `Provider`; `fetch` is globally mocked via `vitest-fetch-mock` (wired up in `src/setupTests.js`), so give it a `mockResponse`/`mockResponseOnce` before rendering anything that fetches on mount.

### Known encoding/platform traps

- `api/requirements.txt` is UTF-8-with-BOM (not plain UTF-8, not UTF-16 — it's been both at different points in this repo's history after tooling round-trips). If you edit it, verify the byte-level encoding survived (`open(path, 'rb').read()[:5]` should start `\xef\xbb\xbf`) before committing — a naive text edit through a tool that assumes ASCII/UTF-8-without-BOM can silently corrupt it, and Git will refuse to line-merge it (reports "Cannot merge binary files") if two branches touch it with different encodings.
- Files containing JSX must use the `.jsx` extension (Vite does not parse JSX in `.js`). Imports must match filename casing exactly — Windows/macOS filesystems are case-insensitive so a wrong-case import (e.g. `./app` for `App.js`) works locally and only breaks the production build on Linux (this happened for real; see `src/index.js`'s git history).
- React 19 ignores `defaultProps` and `propTypes` on function components; use default parameter values. Class components under `connect` get a fresh props object on every render (react-redux passes a `ref` prop, which React 19 strips by copying), so never compare `prevProps !== this.props` in `componentDidUpdate` — compare the prop values (see `config.jsx`), or it loops forever.
