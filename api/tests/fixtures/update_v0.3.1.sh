#!/bin/bash
#
# SmokerPi updater: downloads the latest GitHub release bundle (smokerpi.tar.gz),
# installs it over this directory, and restarts the service.
#
#   sudo ./update.sh          update if a newer release exists
#   sudo ./update.sh --force  reinstall the latest release even if up to date
#
# Preserved across updates: api/config.json, api/venv, api/log.

set -euo pipefail

REPO="Phazeshift/smokerpi"
SERVICE="smokerpiboot"

main() {
    local dir force="${1:-}"
    dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$dir"

    local latest_url latest current
    latest_url="$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$REPO/releases/latest")"
    latest="${latest_url##*/}"
    current="$(cat VERSION 2>/dev/null || echo none)"

    if [[ "$latest" == "$current" && "$force" != "--force" ]]; then
        echo "Already up to date ($current)."
        return 0
    fi
    echo "Updating $current -> $latest"

    local tmp
    tmp="$(mktemp -d)"
    trap "rm -rf '$tmp'" EXIT
    curl -fsSL -o "$tmp/smokerpi.tar.gz" "https://github.com/$REPO/releases/download/$latest/smokerpi.tar.gz"
    tar -xzf "$tmp/smokerpi.tar.gz" -C "$tmp"
    local new="$tmp/smokerpi"

    # Install Python deps first so a failure leaves the running install untouched.
    if ! cmp -s api/requirements.txt "$new/api/requirements.txt"; then
        if ! api/venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
            echo "This release needs Python 3.9 or newer, but the venv uses $(api/venv/bin/python --version 2>&1)." >&2
            echo "Upgrade Raspberry Pi OS and reinstall (see the README); nothing has been changed." >&2
            return 1
        fi
        echo "requirements.txt changed; installing Python dependencies"
        api/venv/bin/pip install -r "$new/api/requirements.txt"
    fi

    rm -rf build api/smokerpi
    cp -r "$new/build" build
    cp -r "$new/api/smokerpi" api/smokerpi
    cp "$new/api/runserver.py" "$new/api/requirements.txt" "$new/api/.flaskenv" api/
    cp "$new/runserver.sh" "$new/install.sh" "$new/smokerpiboot" .
    chmod +x runserver.sh install.sh
    # update.sh itself is replaced last, below; bash has already parsed main().
    cp "$new/update.sh" update.sh
    chmod +x update.sh
    echo "$latest" > VERSION

    if [[ -x "/etc/init.d/$SERVICE" ]]; then
        service "$SERVICE" restart
    else
        echo "Service '$SERVICE' is not installed; start SmokerPi manually (./runserver.sh)."
    fi
    echo "Now running $latest."
}

# Everything above is parsed before it runs, and we exit before bash could read
# any bytes of this file that changed underneath it when update.sh is replaced.
main "$@"
exit $?
