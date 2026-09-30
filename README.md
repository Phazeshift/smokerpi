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
- **`blower_minimum`** used to be a setting but the control loop stopped reading it when the damper was added (the blower is simply on when the PID output is above 99, otherwise off), so it was removed. An old `config.json` that still contains it is fine: it is ignored.
- **Before reinstalling the OS**, back the file up, e.g. `cp api/config.json ~/smokerpi-config.json`, and copy it back into `api/` before the first start. Otherwise the defaults are used, and with them a fully open servo range of 500-2500 us instead of 500-1500 us.
