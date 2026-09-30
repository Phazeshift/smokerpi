# smokerpi
Raspberri Pi app for smoker blower control and temp monitoring

## Deploying to the Pi

First install: copy a release bundle onto the Pi (or clone the repo), then run `sudo ./install.sh` as described in that script.

Updating: `sudo ./update.sh` downloads the latest GitHub Release (`smokerpi.tar.gz`), installs it, and restarts the service. `sudo ./update.sh --force` reinstalls the current release.

Releasing (maintainers): after CI is green on `master`, push a tag, e.g. `git tag v1.2.3 && git push origin v1.2.3`. The Release workflow builds and publishes the bundle.
