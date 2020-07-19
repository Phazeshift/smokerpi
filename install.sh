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

#Install pip & Flask
apt-get -y install python-setuptools python-dev python3-pip

cd api
#pip install virtualenv
python3 -m venv venv
source "./venv/bin/activate"
pip install -r requirements.txt
cd .. 

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
