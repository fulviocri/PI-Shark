#!/pi-tail/venv/bin/python

import os
import atexit
import signal
import sys
import subprocess
from datetime import datetime
from time import sleep
import logging

import ipaddress
import socket
import requests
import nmap

from scapy.config import conf
from scapy.all import Ether, UDP, BOOTP, DHCP, srp, IP, get_if_raw_hwaddr, sniff, ARP

# ===========================================================================================================

conf.checkIPaddr = False

pid_file = "/run/pi-tail.pid"
scan_file = None

device_name = "ICS Advent DM9601 Fast Ethernet Adapter"
interface = "eth0"
timeout = 10
verbose = True
multi = False

dhcp_ip = None
my_ip = None
my_mask = None
target_network = None

dhcp_options = {"dhcp_server": None, "offered_ip": None, "subnet_mask": None, "cidr_mask": None, "router": None}

# ===========================================================================================================
# Configure logging
logging.basicConfig(filename='pi-tail.log', level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()

# ===========================================================================================================
def main():
    atexit.register(cleanup)
    pid = os.getpid()
    save_pid_to_file(pid)

    print("")
    print("===========================================================================================================")

    main_screen()
    check_usb_device(device_name)

    if check_dhcp_server():
        assign_ip()
    elif monitor_arp_traffic():
        assign_ip()
    
    if check_internet_connection(): get_public_ip()
    network_scan()

# ===========================================================================================================
def create_scan_file():
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    scan_file = f"/pi-tail/scan/{timestamp}-{target_network}.log"

    print("")

    try:
        with open(scan_file, 'w'):
            pass
        print(f"File {scan_file} successfully created.")
    except Exception as e:
        print(f"Error creating file {scan_file}: {e}")

# ===========================================================================================================
def save_pid_to_file(pid):
    print("")
    print("Saving PID info to file:")

    try:
        with open(pid_file, 'w') as f:
            f.write(str(pid))
        print(f"  PID {pid} saved successfully in {pid_file}")
    except Exception as e:
        print(f"  Error saving PID: {e}")

# ===========================================================================================================
def main_screen():
    os.system('clear')

    print("")
    print( " ███████████                                         ███████████  █████")
    print( "░░███░░░░░███                                       ░░███░░░░░███░░███ ")
    print( " ░███    ░███   ██████   ██████   ██████  ████████   ░███    ░███ ░███ ")
    print( " ░██████████   ███░░███ ███░░███ ███░░███░░███░░███  ░██████████  ░███ ")
    print( " ░███░░░░░███ ░███████ ░███ ░░░ ░███ ░███ ░███ ░███  ░███░░░░░░   ░███ ")
    print( " ░███    ░███ ░███░░░  ░███  ███░███ ░███ ░███ ░███  ░███         ░███ ")
    print( " █████   █████░░██████ ░░██████ ░░██████  ████ █████ █████        █████")
    print( "░░░░░   ░░░░░  ░░░░░░   ░░░░░░   ░░░░░░  ░░░░ ░░░░░ ░░░░░        ░░░░░ ")
    print("")
    print("")

# ===========================================================================================================
def check_usb_device(device_name):
    print("")
    print("Checking Ethernet adapter status:")

    while True:
        lsusb_output = subprocess.run(["lsusb"], capture_output=True, text=True).stdout
        if device_name in lsusb_output:
            print(f"  Interface {interface} is connected.")
            print(f"  Changing MAC Address on {interface}.")
            command = f"macchanger -r {interface}"
            subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            print(f"  Disabling IPv6 on {interface}.")
            command = f"sysctl -w net.ipv6.conf.{interface}.disable_ipv6=1"
            subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            print(f"  Enabling interface {interface}.")
            command = f"ip link set dev {interface} arp off up"
            subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        else:
            print("  Waiting for the Ethernet adapter to be connected...")
            sleep(1)

# ===========================================================================================================
def check_dhcp_server():
    global dhcp_ip, my_ip, my_mask, target_network

    print("")
    print("Looking for DHCP server on network:")

    fam, hw = get_if_raw_hwaddr(interface)
    dhcp_discover = Ether(dst="ff:ff:ff:ff:ff:ff")/IP(src="0.0.0.0",dst="255.255.255.255")/UDP(sport=68,dport=67)/BOOTP(chaddr=hw)/DHCP(options=[("message-type","discover"),"end"])
    responses, _  = srp(dhcp_discover, multi=multi, timeout=timeout, verbose=verbose)

    try:
        for response in responses:
            dhcp_options = extract_dhcp_options(response[1])
            dhcp_options["dhcp_server"] = response[1][IP].src
            dhcp_options["offered_ip"] = response[1][BOOTP].yiaddr

            dhcp_ip = dhcp_options["dhcp_server"]
            my_ip = dhcp_options["offered_ip"]
            my_mask = dhcp_options["cidr_mask"]

            target_network = ipaddress.ip_network(my_ip + my_mask, strict=False)
        
        if response[1][IP].src:
            print(f"  Found a DHCP server with IP: {dhcp_ip}")
            print(f"  DHCP server offered IP: {my_ip}/{my_mask}")
            return True
        else:
            print("  No DHCP server found in the network.")
            return False
    except:
        print("  ERROR: No DHCP server found in the network.")
        return False

# ===========================================================================================================
def extract_dhcp_options(packet):
    if DHCP in packet and packet[DHCP].options:
        for option in packet[DHCP].options:
            if option[0] == "subnet_mask":
                dhcp_options["subnet_mask"] = option[1]
                dhcp_options["cidr_mask"] = ipaddress.IPv4Network((0,dhcp_options["subnet_mask"])).prefixlen
            elif option[0] == "router":
                dhcp_options["router"] = option[1]
    
    return dhcp_options

# ===========================================================================================================
def monitor_arp_traffic():
    print("")
    print("Start monitoring ARP traffic on network:")

    try:
        a = sniff(iface=interface, prn=process_arp_packet, filter="arp", store=0, timeout=timeout, count=1)
        print(f"  Found a free IP: {my_ip}")
        return True
    except:
        print(f"  No ARP traffic detected on {interface}")
        return False

# ===========================================================================================================
def process_arp_packet(packet):
    global my_ip, my_mask, target_network

    if packet[ARP].op == 1:
        print(f"  ARP Request received from: {packet[ARP].psrc}")
        target_network = ipaddress.ip_network(packet[ARP].psrc + "/24", strict=False)
    
    for ip in target_network.hosts():
        try:
            command = f"arping -i {interface} -0 -c 1 -r {ip}"
            subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            my_ip = ip
            my_mask = "24"
            return None

# ===========================================================================================================
def assign_ip():
    print("")
    print("Starting IP address configuration:")
    
    if my_ip is not None:
        print(f"  Assigning IP address {my_ip}/{my_mask} to {interface}.")
        command = f"ip addr add {my_ip}/{my_mask} dev {interface}"
        subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ===========================================================================================================
def check_internet_connection(host="45.33.32.156", port=80, timeout=3):
    print("")
    print("Checking for Internet connection:")

    socket.setdefaulttimeout(timeout)
    socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        socket.connect((host, port))
        print("  Internet connection is available")
        return True
    except Exception as e:
        print("  Internet connection is NOT available")
        return False

# ===========================================================================================================
def get_public_ip():
    try:
        response = requests.get('https://ifconfig.me/ip')

        if response.status_code == 200:
            print(f"  Public IP address: {response.text}")
            return response.text
        else:
            print("  Cannot get public IP address. Error in HTTP request")
            return False
    except Exception as e:
        print(f"  Error while retrieving public IP address: {str(e)}")
        return False

# ===========================================================================================================
def network_scan():
    print("")
    print("Starting network scan on subnet:")

    create_scan_file()

    net_scanner = nmap.PortScanner()
    target = "scanme.nmap.org"
    options = "-sS -sV -O -A -p 1-1000"
    net_scanner.scan(target, arguments=options)

    for host in net_scanner.all_hosts():
        print(f"  Host: {host} | {net_scanner[host].state()}")

# ===========================================================================================================
def signal_handler(sig, frame):
    print("")
    print('You pressed Ctrl+C!')
    
    sys.exit(1)

# ===========================================================================================================
def cleanup():
    print("")
    print("Starting cleanup:")

    # try:
    #     print(f"  IP address {my_ip} removed from {interface}.")
    #     command = f"ip addr del {my_ip}/{my_mask} dev {interface}"
    #     subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL)
    # except Exception as e:
    #     print(f"  Error removing IP address {my_ip} from interface {interface}: {e}")

    # try:
    #     print(f"  Interface {interface} disabled.")
    #     command = f"ip link set dev {interface} arp off down"
    #     subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL)
    # except Exception as e:
    #     print(f"  Error disabling interface {interface}: {e}")
    
    # try:
    #     print(f"  MAC Address restored on {interface}.")
    #     command = f"macchanger -p {interface}"
    #     subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL)
    # except Exception as e:
    #     print(f"  Error restoring MAC Address on interface {interface} {e}")
    
    try:
        os.remove(pid_file)
        print(f"  PID file {pid_file} deleted successfully.")
    except Exception as e:
        print(f"  Error deleting PID file {pid_file}: {e}")

# ===========================================================================================================
if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    if os.path.exists(pid_file):
        print("The PID file already exists. The script will be terminated.")
        sys.exit(1)
    
    main()
