#!/bin/bash

# prepare any message you want
hostname="$(hostname)"
host_ip="$(awk '/inet / && $2 != "127.0.0.1"{print $2}' <(ifconfig))"
#login_ip="$(echo $SSH_CONNECTION | cut -d " " -f 1)"
login_date="$(date +"%e %b %Y, %a %r")"
login_name="$(whoami)"

# For new line I use $'\n' here
message="$hostname is up and running."$'\n'"IP Address is: $host_ip"$'\n'"$login_date"

#send it to telegram
telegram-send "$message"