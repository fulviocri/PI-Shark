#!/bin/bash

userdel -r admin

rfkill unblock wifi
for filename in /var/lib/systemd/rfkill/*:wlan ; do
    echo 0 > $filename
done

ufw default deny incoming
ufw default allow outgoing
ufw deny in on eth0
ufw allow in on wlan0 to any port ssh
ufw allow in on usb0 to any port ssh
yes | ufw enable

rm /setup.sh
rm /etc/profile.d/firstboot.sh
