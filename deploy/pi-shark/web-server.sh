#!/bin/bash

pid_file=/run/web-server.pid

if [ "$#" -ne 1 ]; then
    echo "ERROR: Invalid syntax"
    exit 1
fi

if [ "$1" == "start" ]; then
    nohup python -m http.server 8000 & >/dev/null 2>&1
    pid=$!
    echo $pid > $pid_file
    ufw allow in on wlan0 to any port 8000 >/dev/null 2>&1
    ufw reload >/dev/null 2>&1
    exit 0
fi

if [ "$1" == "stop" ]; then
    if [ -f $pid_file ]; then
        pid="$(cat $pid_file)" >/dev/null 2>&1
        kill $pid >/dev/null 2>&1
        rm $pid_file >/dev/null 2>&1
        ufw delete allow in on wlan0 to any port 8000 >/dev/null 2>&1
        ufw reload >/dev/null 2>&1
    else
        echo "Python web-server is not running"
    fi
    exit 0
fi

if [ "$1" == "-h" ]; then
    echo "Usage: $0 COMMAND"
    echo ""
    echo "COMMAND:"
    echo " start                    Start the python integrated webserver"
    echo " stop                     Stop the python integrated webserver"
    exit 0
fi