# smokerpi
Raspberri Pi app for smoker blower control and temp monitoring

## Deploying to the Pi

Requirements: a Raspberry Pi OS with **Python 3.9 or newer** (Bullseye or later) — the pinned backend packages (Flask 3, Werkzeug 3, ...) do not install on older Pythons.

First install: copy a release bundle onto the Pi (or clone the repo), then run `sudo ./install.sh` as described in that script.

Updating: `sudo ./update.sh` downloads the latest GitHub Release (`smokerpi.tar.gz`), installs it, and restarts the service. `sudo ./update.sh --force` reinstalls the current release.

Releasing (maintainers): after CI is green on `master`, push a tag, e.g. `git tag v1.2.3 && git push origin v1.2.3`. The Release workflow builds and publishes the bundle.

## Hardware configuration

The wiring and settings of the smoker's Pi, as reported by the running app (`/api/config`) on 2026-09-30, so the install can be recreated, for example after reinstalling the OS. Pin numbers are BCM (GPIO) numbers; the header pin is the physical pin on the standard 40-pin Raspberry Pi header.

| Function | Config key | BCM GPIO | Header pin |
| --- | --- | --- | --- |
| MAX31855 thermocouple: chip select (CS) | `cs_pin` | 20 | 38 |
| MAX31855 thermocouple: clock (SCK) | `clock_pin` | 21 | 40 |
| MAX31855 thermocouple: data out (SO) | `data_pin` | 16 | 36 |
| Blower: drive / PWM output | `blower_pin1` | 26 | 37 |
| Blower: second input (held low) | `blower_pin2` | 19 | 35 |
| Damper: servo signal | `damper_pin` | 13 | 33 |

- **Thermocouple:** a MAX31855 read over software (bit-banged) SPI on those three GPIOs, so the Pi's SPI interface does not need enabling. It reports degrees Celsius in 0.25 degree steps.
- **Blower:** two outputs, wired like a motor driver's two inputs. Pin 1 high with pin 2 low is on, both low is off, and partial speed is 100 Hz PWM on pin 1.
- **Damper:** a hobby servo driven through [pigpio](https://abyz.me.uk/rpi/pigpio/), so the `pigpiod` daemon must be running (`sudo apt install pigpio && sudo systemctl enable --now pigpiod`; `install.sh` offers to do this). The servo is only pulsed for about a second per move.

### Settings

| Key | Our Pi | Default | Meaning |
| --- | --- | --- | --- |
| `set_temperature` | 105 | 105 | Target pit temperature in degrees Celsius (the PID setpoint). |
| `damper_minimum` | 500 | 500 | Servo pulse width in microseconds with the damper closed (0%). |
| `damper_maximum` | **1500** | 2500 | Servo pulse width in microseconds with the damper fully open (100%). **The only value that differs from the default**: it limits the servo's travel to 500-1500 us. |
| `worker_interval` | 10 | 10 | Seconds between thermocouple reads / PID updates. |
| `graph_interval` | 10 | 10 | Minimum seconds between graph points (the last 2000 are kept). |
| `cs_pin`, `clock_pin`, `data_pin`, `blower_pin1`, `blower_pin2`, `damper_pin` | see the table above | same | Pins. |

### config.json

The settings live in `api/config.json` in the install directory. It is created with the defaults on first start, is not in git, and is preserved by `update.sh`. Only keys that differ from the defaults need to be in it, so this Pi's file is just:

```json
{"damper_maximum": 1500}
```

(The running app reported every other value equal to the default. If you change the target temperature on the Config page it is saved into this file too.)

- **Changing settings:** the three editable settings (`set_temperature`, `damper_minimum`, `damper_maximum`) can be changed on the Config page and apply immediately. Pins and intervals are read-only there because they only take effect at startup: edit `config.json` on the Pi and restart with `sudo service smokerpiboot restart`.
- **PID gains:** `pid_kp`, `pid_ki` and `pid_kd` (defaults 1, 0.1, 0.05, the values that used to be hardcoded) can be changed on the Config page (PID tuning) and apply to the running controller immediately, or edited in `config.json`. The controller stops its integral term growing while the output is saturated (anti-windup). Note that `pid_ki` is per second and the loop runs every ~11 s, so the default Ki of 0.1 is an integral time of only 10 s, far quicker than a smoker responds. In a rough simulation (not your smoker) `pid_kp` 5, `pid_ki` 0.005, `pid_kd` 0 removed the overshoot, at the cost of a slower warm-up (about 50 minutes instead of 16). Try values like those once there is a fire, and treat them as a starting point only.
- **Password:** with no `password` in `config.json` anyone on the network can open the damper, run the blower and change the set temperature, and the log says so at startup. Set `"password": "something"` and restart to require it: the browser asks once (HTTP Basic auth, any username) for the page and the API alike. The password is stored as plain text in `config.json`, is never returned by the API and cannot be changed over it. This is protection against casual access on a trusted network, not encryption: the connection is plain HTTP, so do not expose the port to the internet.
- **`blower_minimum`** used to be a setting but the control loop stopped reading it when the damper was added (the blower is simply on when the PID output is above 99, otherwise off), so it was removed. An old `config.json` that still contains it is fine: it is ignored.
- **Before reinstalling the OS**, back the file up, e.g. `cp api/config.json ~/smokerpi-config.json`, and copy it back into `api/` before the first start. Otherwise the defaults are used, and with them a fully open servo range of 500-2500 us instead of 500-1500 us.

### Parts and power

This install uses a Raspberry Pi Zero, an MG90S micro servo for the damper (it works with the Pi's 3.3 V signal level; its pulse range is typically about 500-2400 us), and a 5 V USB power bank (3 A) feeding the Pi through the 5 V and GND header pins, with the servo wired to the same 5 V and ground lines. Powering through the header bypasses the Pi's input fuse and protection, so use a regulated 5 V supply and take care not to short it.

### Troubleshooting the damper servo

If the servo clicks, twitches or ignores commands, work from the Pi outwards so you know which part is at fault:

1. **Is pigpiod running?** `pigs t` prints a number if it is. This only proves the daemon accepts commands, not that the servo gets a good signal.
2. **Is the Pi producing the right pulses?** The servo signal is a pulse every 20 ms, so a multimeter on DC volts between the signal pin (GPIO 13, header pin 33) and a GND pin reads its average: 3.3 V x pulse width / 20 ms. With the servo connected, run `pigs s 13 <width>` and compare with the table below. Finish with `pigs s 13 0`, which stops the signal (about 0 V). If the readings match, the Pi and pigpio are fine and the fault is downstream.
3. **Check the servo's supply:** about 4.8 V or more at the servo, steady while it moves, with its ground joined to the Pi's ground.
4. **Check the cable between the Pi and the servo.** On this install an extension lead made three different servos click and ignore most commands (only the longest pulses got through) while the pulses and the supply measured fine; connected directly to the Pi they worked. Keep the signal run short and use a short, good-quality lead. For a long run, buffer the signal at the Pi end (a 74AHCT125 or similar), add a series resistor of about 220 ohm, and put a 470 uF capacitor across the servo's supply.
5. **Test unloaded and stay in range.** Detach the linkage, keep to 500-2500, and do not keep pressing the button while it clicks: a servo with stripped gears wears further with every press.

| `pigs s 13 ...` | Expected average on the signal pin |
| --- | --- |
| 1000 | about 0.17 V |
| 1500 | about 0.25 V |
| 2000 | about 0.33 V |
| 2400 | about 0.40 V |

A servo that clicks can also simply be driven past the end of its travel. To find the real travel, step `pigs s 13 <width>` in 100 us steps and note where the damper is fully closed and fully open, then enter those as `damper_minimum` and `damper_maximum` on the Config page. The app treats the larger pulse as open.
