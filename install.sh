#!/bin/bash
#
# SmokerPi
#
# type the following commands:
# chmod +x install.sh
# sudo ./install.sh
# sudo reboot

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

clear
cat << "EOF"

----------------------------------------------------------------------------

   Welcome to Installation
  ____                  _             ____  _ 
 / ___| _ __ ___   ___ | | _____ _ __|  _ \(_)
 \___ \| '_ ` _ \ / _ \| |/ / _ \ '__| |_) | |
  ___) | | | | | | (_) |   <  __/ |  |  __/| |
 |____/|_| |_| |_|\___/|_|\_\___|_|  |_|   |_|
                                                                                                                       
----------------------------------------------------------------------------

EOF

chmod +x runserver.sh

# The pinned backend packages (Flask 3, Werkzeug 3, ...) need Python 3.9 or newer.
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
    echo "SmokerPi needs Python 3.9 or newer, but this system has $(python3 --version 2>&1)."
    echo "Upgrade Raspberry Pi OS (Bullseye or later) and run this script again."
    exit 1
fi

# python3-venv is a separate package on Debian-based systems. Do not pip install
# virtualenv: recent releases refuse system-wide pip installs, and venv is built in.
apt-get update
apt-get -y install python3-venv python3-pip python3-dev pigpio

cd api
python3 -m venv venv
source "./venv/bin/activate"
pip install -r requirements.txt
cd .. 

while true; do
    read -p "Would you like to start pigpiod automatically after boot? (required for servo / damper support) (y/n): " yn
    case $yn in
        [Yy]* ) systemctl enable pigpiod
            systemctl start pigpiod 
        	break;;
        [Nn]* ) break;;
        * ) echo "Please select (y/n): ";;
    esac
done

while true; do
    read -p "Would you like to start SmokerPi automatically after boot? (y/n): " yn
    case $yn in
        [Yy]* ) sed "s@#DIR#@${PWD}@g" smokerpiboot > /etc/init.d/smokerpiboot

        chmod 755 /etc/init.d/smokerpiboot;
		update-rc.d smokerpiboot defaults;
		break;;
        [Nn]* ) break;;
        * ) echo "Please select (y/n): ";;
    esac
done

