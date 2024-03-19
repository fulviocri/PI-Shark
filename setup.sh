#!/bin/bash

if [ $(id -u) -ne 0 ]
	then echo "Please run as root"
	exit 1
fi

clear

echo ""
echo "  ███████████  █████             █████████  █████                          █████          █████████            █████                        "
echo " ░░███░░░░░███░░███             ███░░░░░███░░███                          ░░███          ███░░░░░███          ░░███                         "
echo "  ░███    ░███ ░███            ░███    ░░░  ░███████    ██████   ████████  ░███ █████   ░███    ░░░   ██████  ███████   █████ ████ ████████ "
echo "  ░██████████  ░███  ██████████░░█████████  ░███░░███  ░░░░░███ ░░███░░███ ░███░░███    ░░█████████  ███░░███░░░███░   ░░███ ░███ ░░███░░███"
echo "  ░███░░░░░░   ░███ ░░░░░░░░░░  ░░░░░░░░███ ░███ ░███   ███████  ░███ ░░░  ░██████░      ░░░░░░░░███░███████   ░███     ░███ ░███  ░███ ░███"
echo "  ░███         ░███             ███    ░███ ░███ ░███  ███░░███  ░███      ░███░░███     ███    ░███░███░░░    ░███ ███ ░███ ░███  ░███ ░███"
echo "  █████        █████           ░░█████████  ████ █████░░████████ █████     ████ █████   ░░█████████ ░░██████   ░░█████  ░░████████ ░███████ "
echo " ░░░░░        ░░░░░             ░░░░░░░░░  ░░░░ ░░░░░  ░░░░░░░░ ░░░░░     ░░░░ ░░░░░     ░░░░░░░░░   ░░░░░░     ░░░░░    ░░░░░░░░  ░███░░░  "
echo "                                                                                                                                   ░███     "
echo "                                                                                                                                   █████    "
echo "                                                                                                                                  ░░░░░     "
echo ""
echo ""

# ========================================================================================================================================================================
# Setting the password for the root user account
setrootpassword() {
	echo ""
	echo "Setting the password for root user account:"
	echo -e "New password: "
	read -s root_password_1

	echo -e "Retype new password: "
	read -s root_password_2

	if [ $root_password_1 != $root_password_2 ]; then
		echo "Passwords do not match"
		setrootpassword
	fi

	echo -e "$root_password_1\n$root_password_1" | passwd root >/dev/null 2>&1
	echo ""
	if [ $? -eq 0 ]; then
		echo "Password changed successfully"
	else
		echo "Password change error"
		exit 1
	fi

	echo "DONE"
}

# ========================================================================================================================================================================
# Setting the current date & time
changecurrentdatetime() {
	echo ""
	echo "Setting the current date and time:"
	date
	read -p "Is the current date and time correct? (y/n): " correct_date

	if [[ $correct_date == "n" ]]; then
		read -p "Enter date and time (YYYY-MM-DD HH:MM:SS): " current_date
		timedatectl set-ntp false >/dev/null 2>&1
		timedatectl set-time "$current_date" >/dev/null 2>&1

		if [ $? -eq 0 ]; then
			timedatectl set-ntp true >/dev/null 2>&1
			date
		else
			changecurrentdatetime
		fi
	fi

	echo "DONE"
}

# ========================================================================================================================================================================
# Setting FQDN host name
sethostname() {
	echo ""
	echo "Setting FQDN host name"
	read -p "[Press enter to continue]"

	hostnamectl set-hostname pi-tail >/dev/null 2>&1
	hostnamectl set-hostname pi-tail.local >/dev/null 2>&1

	echo "DONE"
}

# ========================================================================================================================================================================
# Cleaning up system
cleanupsystem() {
	echo ""
	echo "Cleaning up system"
	read -p "[Press enter to continue]"

    if systemctl -all list-unit-files alsa-restore.service | grep "alsa-restore.service enabled" >/dev/null 2>&1 ;then
		echo "Disabling alsa-restore.service"
	    systemctl disable alsa-restore.service >/dev/null 2>&1
	    systemctl stop alsa-restore.service >/dev/null 2>&1
    fi

    if systemctl -all list-unit-files bluetooth.service | grep "bluetooth.service enabled" >/dev/null 2>&1 ;then
		echo "Disabling bluetooth.service"
	    systemctl disable bluetooth.service >/dev/null 2>&1
	    systemctl stop bluetooth.service >/dev/null 2>&1
    fi

    if systemctl -all list-unit-files bthelper@hci0.service | grep "bthelper@hci0.service enabled" >/dev/null 2>&1 ;then
		echo "Disabling bthelper@hci0.service"
	    systemctl disable bthelper@hci0.service >/dev/null 2>&1
	    systemctl stop bthelper@hci0.service >/dev/null 2>&1
    fi

    if systemctl -all list-unit-files systemd-networkd-wait-online.service | grep "systemd-networkd-wait-online.service enabled" >/dev/null 2>&1 ;then
		echo "Disabling systemd-networkd-wait-online.service"
	    systemctl disable systemd-networkd-wait-online.service >/dev/null 2>&1
	    systemctl stop systemd-networkd-wait-online.service >/dev/null 2>&1
    fi

    if systemctl -all list-unit-files triggerhappy.service | grep "triggerhappy.service enabled" >/dev/null 2>&1 ;then
		echo "Disabling triggerhappy.service"
	    systemctl disable triggerhappy.service >/dev/null 2>&1
	    systemctl stop triggerhappy.service >/dev/null 2>&1

        systemctl disable triggerhappy.socket >/dev/null 2>&1
        systemctl stop triggerhappy.socket >/dev/null 2>&1
    fi

    if systemctl -all list-unit-files ModemManager | grep "ModemManager enabled" >/dev/null 2>&1 ;then
		echo "Uninstalling ModemManager"
		apt-get remove --purge modemmanager >/dev/null 2>&1
    fi

	echo "Removing unused packages"
	apt-get -y autoremove --purge >/dev/null 2>&1

	echo "DONE"
}

# ========================================================================================================================================================================
# System update
systemupdate() {
	echo ""
	echo "Starting system update"
	read -p "[Press enter to continue]"

	UPDATENUM=$(apt-get -q -y --ignore-hold --allow-change-held-packages --allow-unauthenticated -s dist-upgrade | /bin/grep  ^Inst | wc -l)

	echo "Package to update: $UPDATENUM"

	apt-get update >/dev/null 2>&1
	apt-get -y upgrade >/dev/null 2>&1

	echo "DONE"
}

# ========================================================================================================================================================================
# Installing base component
installbasecomponent() {
	echo ""
	echo "Installing base component"
	read -p "[Press enter to continue]"

	apt-get install -y build-essential git curl xsltproc rsync tmux >/dev/null 2>&1

	echo "DONE"
}

# ========================================================================================================================================================================
# Installing networking component
installnetworkcomponent() {
	echo ""
	echo "Installing networking component"
	read -p "[Press enter to continue]"
	
	apt-get install -y i2c-tools ufw >/dev/null 2>&1
	apt-get install -y python3-pip python3-venv python3-smbus >/dev/null 2>&1
	apt-get install -y nmap tcpdump doscan nast ettercap-text-only ncat >/dev/null 2>&1
	apt-get install -y dhcpdump dhcpig dhcp-probe dhcpstarv dhcping >/dev/null 2>&1
	# apt-get install -y arping arpon arp-scan >/dev/null 2>&1
	apt-get install -y arping arp-scan >/dev/null 2>&1
    apt-get install -y dnsenum dnsmap dnsrecon dnswalk dnsutils >/dev/null 2>&1
	apt-get install -y backdoor-factory masscan netdiscover >/dev/null 2>&1
	
	echo "DONE"
}

# ========================================================================================================================================================================
# Configuring UFW firewall
configurefirewall() {
	echo ""
	echo "Configuring UFW firewall"
	read -p "[Press enter to continue]"

	rfkill unblock wifi >/dev/null 2>&1

	ufw default deny incoming >/dev/null 2>&1
	ufw default allow outgoing >/dev/null 2>&1
	ufw deny in on eth0 >/dev/null 2>&1
	ufw allow in on wlan0 to any port ssh >/dev/null 2>&1
	yes | ufw enable >/dev/null 2>&1
	echo "DONE"
}

# ========================================================================================================================================================================
# Copy config file
copyconfigfiles() {
	echo ""
	echo "Copy config files"
	read -p "[Press enter to continue]"
	
	cp -RT /boot/deploy/. / >/dev/null 2>&1

	mv /firstboot.sh /etc/profile.d/firstboot.sh
	
	ln -s /pi-tail/pi-tail.py /usr/bin/pi-tail
	chown root:root /usr/bin/pi-tail
	chmod +x /usr/bin/pi-tail

	ln -s /pi-tail/telegram-send.sh /usr/bin/telegram-send
	chown root:root /usr/bin/telegram-send
	chmod +x /usr/bin/telegram-send

	ln -s /pi-tail/web-server.sh /usr/bin/web-server
	chown root:root /usr/bin/web-server
	chmod +x /usr/bin/web-server

	echo "DONE"
}

# ========================================================================================================================================================================
# Copy config file
pythonvenv() {
	echo ""
	echo "Installing python vEnv and libraries"
	read -p "[Press enter to continue]"

	python3 -m venv /recon-pi/venv >/dev/null 2>&1
	source /recon-pi/venv/bin/activate >/dev/null 2>&1

	pip install python-nmap >/dev/null 2>&1
	pip install netifaces >/dev/null 2>&1
	pip install scapy >/dev/null 2>&1
	pip install requests >/dev/null 2>&1

	deactivate >/dev/null 2>&1

	echo "DONE"
}

# ========================================================================================================================================================================
# Setup completed
setupcomplete() {
	echo ""
	echo "PI-Tail setup completed"
	read -p "[Press enter to reboot]"
	reboot
}

setrootpassword
changecurrentdatetime
sethostname
cleanupsystem
systemupdate
installbasecomponent
installnetworkcomponent
configurefirewall
copyconfigfiles
pythonvenv
setupcomplete