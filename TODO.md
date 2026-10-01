# TODO

Last updated 2026-10-01, after release v0.3.2.

## State of play

- **Released: v0.3.2.** All planned dependency migrations are done (Vite/Vitest, React 19, Router 7, Redux 5, Bootstrap 5, recharts 3). The backend runs on Flask 3 / Werkzeug 3 / Python 3.13 on the Pi.
- **Verified on the real Pi (a Pi Zero):** the server stack and version, the config round-trip (identical to the backup), real thermocouple readings (0.25 degree steps), the worker advancing, the Werkzeug debugger no longer exposed, and the blower button (after the GPIO fix in v0.3.2). The damper servo works when wired directly to the Pi; the earlier fault was an extension cable (see "Troubleshooting the damper servo" in the README).
- **Closed recently, do not redo:** exposed debugger (#42), `update.sh` breaking at the end of its own run (#45), `damper_pin` ignored (#43), unused `blower_minimum` removed (#44), the blower never setting its GPIO pins up as outputs plus a worker error silently killing the control loop (#46), config validation and read-only hardware settings (#40), `/config` refresh 404 (#39).
- **Releasing:** after CI is green on `master`, tag `vX.Y.Z`. The Release workflow publishes `smokerpi.tar.gz`; on the Pi run `sudo ./update.sh`. The `update.sh` that does the work is always the previous release's copy (see CLAUDE.md).

## Needs a decision

- [x] **Thermocouple faults.** Done: a missed read keeps the last good reading, and the blower goes off and the PID is skipped once the thermocouple has been silent for `sensor_timeout` (60s). Still to decide: whether a damper position should also be forced on timeout.
- [ ] **Damper direction and travel.** The app treats the larger pulse width as open (`damper_maximum`) and requires `damper_minimum` < `damper_maximum`. Confirm that matches the real damper; if it opens at the smaller pulse, either flip the linkage or add an "invert" setting. Calibrate `damper_minimum` / `damper_maximum` (currently 500 / 1500) against the real damper, using the procedure at the end of "Troubleshooting the damper servo" in the README.

## To do

- [x] **Glitched temperature reads.** Seen on the Pi (2026-10-01, v0.4.0): the very first reading after SmokerPi started was 53.5 when the real value was 26.75 (exactly double: a one-bit slip in the bit-banged SPI read) and no fault was raised. It did not happen on the previous restart, so it is intermittent, and the cause is unproven. Fixed in `MAX31855.get()`: it returns a value only when two consecutive reads agree to within 1 degree, ignores words with a reserved bit (D17, D3) set, and raises `MAX31855Error("Readings do not agree")` after 6 reads (the sensor-timeout grace period then applies). Still to confirm over a long run on the Pi, and a plausibility filter on the size of a jump between passes is not done.
- [x] **PID integral windup.** Found on the Pi (2026-10-01): after sitting saturated at 100 the output stayed at 100 with the reading 1.25 under the target, because the integral had wound up. Fixed by `AntiWindupPID` (`api/smokerpi/pid.py`): the integral does not grow in a step that leaves the output saturated in the direction of the error. The gains are now `pid_kp`/`pid_ki`/`pid_kd` in `config.json` (read at startup, defaults unchanged). **Still open:** in a rough smoker simulation the default gains matter more than anti-windup (Ki 0.1 per second with an ~11 s pass is a 10 s integral time, giving ~8 degrees of overshoot and a sustained oscillation either way), and with them the blower comes on far less during warm-up (about 9% of the time against 33%, and warm-up 22 minutes against 16) because it was only ever reached through windup. Tune the gains on a real fire (the README suggests Kp 5, Ki 0.005, Kd 0 to try), then whether the blower should run during warm-up by design rather than by accident.
- [ ] **Full-loop test on the Pi with the real damper (no fire).** Press the damper button in the UI and confirm it moves. Run the PID and confirm the damper ramps, the blower switches on at saturation (PID output above 99), and the graph keeps advancing the whole time.
- [ ] **Fail-safe test (no fire).** With the PID running, stop pigpiod (`sudo systemctl stop pigpiod`) so the damper call fails. Confirm the graph keeps advancing, the blower goes off and `api/log/app.log` on the Pi records a traceback. Restart SmokerPi afterwards (see the next item for why).
- [x] **The damper reconnects to pigpiod.** Done: `Damper` drops its connection on any error and connects again on the next move (and raises a clear error if pigpiod is still down). Not yet confirmed on the Pi: run the fail-safe test, then start pigpiod again and check the damper moves without restarting SmokerPi.
- [ ] **Reboot test.** Confirm `smokerpiboot` and `pigpiod` start on boot and SmokerPi serves on port 5000 without anyone logging in.
- [ ] **`install.sh` robustness** (found when a venv restored from the old Pi broke the install). After enabling boot start, offer to start the service now: it only registers it, so the app stayed down. Recreate a stale venv (`python3 -m venv --clear venv`) instead of reusing one from an old install. Stop with a clear message when the pip step fails, instead of carrying on and offering to enable a service that cannot start.
- [x] **Show worker failures in the UI.** Done: `/api/state` has `workerError` (failed steps, or a stopped loop via a watchdog) and the status card shows it. The UI polls every 30s, so it can take that long to appear.
- [x] **The app log is bounded.** Done: `configureLogging()` in `api/smokerpi/__init__.py` writes `log/app.log` through a `RotatingFileHandler` (1 MB x 3 backups) at INFO.
- [x] **Test isolation.** Done: an autouse fixture in `api/tests/conftest.py` runs every test in a temp directory, so tests no longer write the real `api/config.json` or `api/log/`; `api/tests/test_isolation.py` guards it.

## Ideas (not decided)

- pigpio is unmaintained and does not support the Pi 5. It works on this Pi Zero (the pulses were measured and are correct), so only revisit if the board changes; `lgpio` or kernel hardware PWM are the alternatives for the damper.
