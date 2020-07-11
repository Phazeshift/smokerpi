#!/bin/bash
#
# CraftBeer PI
#
# type the following commands:
# chmod +x install.sh
# sudo ./install.sh
# sudo reboot


clear
cat << "EOF"

----------------------------------------------------------------------------

   Weclome to Installation

              (                                  (        
              )\ )                 )             )\ )     
             (()/(    )         ( /(    (   (   (()/( (   
              /(_))  (      (   )\())  ))\  )(   /(_)))\  
             (_))    )\  '  )\ ((_)\  /((_)(()\ (_)) ((_) 
             / __| _((_))  ((_)| |(_)(_))   ((_)| _ \ (_) 
             \__ \| '  \()/ _ \| / / / -_) | '_||  _/ | | 
             |___/|_|_|_| \___/|_\_\ \___| |_|  |_|   |_| 
                                             
----------------------------------------------------------------------------

EOF

#Install pip (package installer):
apt-get -y install python-setuptools
easy_install pip

#Install Flask
apt-get -y install python-dev
apt-get -y install libpcre3-dev
cd api
virtualenv venv
source /venv/bin/activate
pip install -r requirements.txt

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
