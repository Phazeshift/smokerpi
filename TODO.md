# TODO

Last updated 2026-10-01, after release v0.3.2.

## State of play

- **Released: v0.3.2.** All planned dependency migrations are done (Vite/Vitest, React 19, Router 7, Redux 5, Bootstrap 5, recharts 3). The backend runs on Flask 3 / Werkzeug 3 / Python 3.13 on the Pi.
- **Verified on the real Pi (a Pi Zero):** the server stack and version, the config round-trip (identical to the backup), real thermocouple readings (0.25 degree steps), the worker advancing, the Werkzeug debugger no longer exposed, and the blower button (after the GPIO fix in v0.3.2). The damper servo works when wired directly to the Pi; the earlier fault was an extension cable (see "Troubleshooting the damper servo" in the README).
- **Closed recently, do not redo:** exposed debugger (#42), `update.sh` breaking at the end of its own run (#45), `damper_pin` ignored (#43), unused `blower_minimum` removed (#44), the blower never setting its GPIO pins up as outputs plus a worker error silently killing the control loop (#46), config validation and read-only hardware settings (#40), `/config` refresh 404 (#39).
- **Releasing:** after CI is green on `master`, tag `vX.Y.Z`. The Release workflow publishes `smokerpi.tar.gz`; on the Pi run `sudo ./update.sh`. The `update.sh` that does the work is always the previous release's copy (see CLAUDE.md).

## Needs a decision

- [ ] **Thermocouple faults.** `MAX31855Error` (for example an open or shorted thermocouple) is swallowed in `monitorTemp` (`api/smokerpi/__init__.py`), so the PID keeps driving the damper and blower from the **last good reading**. Safer: treat it as a failed step, log it, switch the blower off (the existing fail-safe) and skip the PID, retrying every pass. This changes how the control loop behaves, so decide before a real fire goes on it.
- [ ] **Damper direction and travel.** The app treats the larger pulse width as open (`damper_maximum`) and requires `damper_minimum` < `damper_maximum`. Confirm that matches the real damper; if it opens at the smaller pulse, either flip the linkage or add an "invert" setting. Calibrate `damper_minimum` / `damper_maximum` (currently 500 / 1500) against the real damper, using the procedure at the end of "Troubleshooting the damper servo" in the README.

## To do

- [ ] **Full-loop test on the Pi with the real damper (no fire).** Press the damper button in the UI and confirm it moves. Run the PID and confirm the damper ramps, the blower switches on at saturation (PID output above 99), and the graph keeps advancing the whole time.
- [ ] **Fail-safe test (no fire).** With the PID running, stop pigpiod (`sudo systemctl stop pigpiod`) so the damper call fails. Confirm the graph keeps advancing, the blower goes off and `api/log/app.log` on the Pi records a traceback. Restart SmokerPi afterwards (see the next item for why).
- [ ] **The damper probably never reconnects to pigpiod.** `Damper.__init__` opens one `pigpio.pi()` connection and keeps it, so if pigpiod is restarted or crashes the damper would keep failing until SmokerPi itself is restarted. Verify with the fail-safe test above, then reconnect on error.
- [ ] **Reboot test.** Confirm `smokerpiboot` and `pigpiod` start on boot and SmokerPi serves on port 5000 without anyone logging in.
- [ ] **`install.sh` robustness** (found when a venv restored from the old Pi broke the install). After enabling boot start, offer to start the service now: it only registers it, so the app stayed down. Recreate a stale venv (`python3 -m venv --clear venv`) instead of reusing one from an old install. Stop with a clear message when the pip step fails, instead of carrying on and offering to enable a service that cannot start.
- [ ] **Show worker failures in the UI.** The worker now survives errors and fails safe, but a failure is only logged. Expose it (for example a `workerError` in `/api/state`) and show it in the existing error banner.
- [ ] **The app log is unbounded.** `create_app()` uses `logging.basicConfig(filename='./log/app.log', level=logging.DEBUG)`, and `RotatingFileHandler` is imported but never used. Rotate it (and consider INFO) so it cannot fill the Pi's SD card.
- [ ] **Test isolation.** `TestConfigEndpoint::test_post_updates_config_and_dependent_hardware` (`api/tests/test_api.py`) saves into the real `api/config.json`, because only one test in that file changes into a temp directory and `conftest.py` does not. Add an autouse fixture in `conftest.py` that chdirs to `tmp_path`. Until then, running the tests overwrites a developer's local config.

## Ideas (not decided)

- pigpio is unmaintained and does not support the Pi 5. It works on this Pi Zero (the pulses were measured and are correct), so only revisit if the board changes; `lgpio` or kernel hardware PWM are the alternatives for the damper.
