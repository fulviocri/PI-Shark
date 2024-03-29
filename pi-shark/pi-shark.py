#!/usr/bin/python3

import os
import sys
import atexit
import signal
import subprocess
import logging
import ipaddress
import socket
import requests
import nmap

from datetime import datetime
from time import sleep

from scapy.config import conf
from scapy.all import Ether, UDP, BOOTP, DHCP, srp, IP, get_if_raw_hwaddr, sniff, ARP

# ===========================================================================================================

app_version = "0.5"


pid_file = "/run/pi-tail.pid"
log_file = "/var/log/pi-shark.log"

interface = "eth0"
interface_arp = "off"

scan_file = None
scan_timeout = 10
scan_verbose = True
scan_multi = False

conf.checkIPaddr = False
conf.iface = interface

dhcp_ip = None
my_ip = None
my_mask = None
target_network = None

dhcp_options = {"dhcp_server": None, "offered_ip": None, "subnet_mask": None, "cidr_mask": None, "router": None}

# ===========================================================================================================
# Configure logging
logging.basicConfig(level=logging.INFO, filename=log_file, filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# ===========================================================================================================
def main():
    atexit.register(cleanup)

    pid = os.getpid()
    save_pid_to_file(pid)

    if config_interface() is False: cleanup()

    if check_dhcp_server():
        assign_ip()
    elif monitor_arp_traffic():
        assign_ip()

    if check_internet_connection(): get_public_ip()
    network_scan()

# ===========================================================================================================
def create_scan_file():
    global scan_file

    now = datetime.now()
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    scan_file = f"/pi-shark/scan/{timestamp}.log"

    try:
        with open(scan_file, 'w'):
            pass
        logging.info(f"  File {scan_file} successfully created")
        return True
    except Exception as e:
        logging.error(f" Cannot create file {scan_file}: {e}")
        return False

# ===========================================================================================================
def save_pid_to_file(pid):
    logging.info("")
    logging.info("Saving PID info to file:")

    try:
        with open(pid_file, 'w') as f:
            f.write(str(pid))
        logging.info(f"  PID {pid} saved successfully to {pid_file}")
    except Exception as e:
        logging.error(f" Cannot save PID: {e}")

# ===========================================================================================================
def config_interface():
    logging.info("")
    logging.info(f"Configuring Ethernet adapter {interface}:")

    try:
        logging.info(f"  Changing MAC Address on {interface}")
        command = f"macchanger -r {interface}"
        subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logging.error(f" Cannot change MAC Address: {e}")
        return False

    try:
        logging.info(f"  Disabling IPv6 on {interface}")
        command = f"sysctl -w net.ipv6.conf.{interface}.disable_ipv6=1"
        subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logging.error(f" Cannot disable IPv6: {e}")
        return False

    try:
       logging.info(f"  Enabling interface {interface}")
       command = f"ip link set dev {interface} arp {interface_arp} up"
       subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logging.error(f" Cannot enable interface: {e}")
        return False

    return True

# ===========================================================================================================
def check_dhcp_server():
    global dhcp_ip, my_ip, my_mask, target_network

    logging.info("")
    logging.info("Looking for DHCP server on network:")

    fam, hw = get_if_raw_hwaddr(interface)
    dhcp_discover = Ether(dst="ff:ff:ff:ff:ff:ff")/IP(src="0.0.0.0",dst="255.255.255.255")/UDP(sport=68,dport=67)/BOOTP(chaddr=hw)/DHCP(options=[("message-type","discover"),"end"])
    responses, _  = srp(dhcp_discover, multi=scan_multi, timeout=scan_timeout, verbose=scan_verbose)

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
            logging.info(f"  Found a DHCP server with IP: {dhcp_ip}")
            logging.info(f"  DHCP server offered IP: {my_ip}/{my_mask}")
            return True
        else:
            logging.info("  No DHCP server found in the network.")
            return False
    except Exception as e:
        logging.error(f" {e}")
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
    logging.info("")
    logging.info("Start monitoring ARP traffic on network:")

    try:
        #a = sniff(iface=interface, prn=process_arp_packet, filter="arp", store=0, timeout=timeout, count=10)
        arp_packet = sniff(iface=interface, filter="arp", count=10)
        arp_packet[1]

        logging.info(f"  Found a free IP: {my_ip}")
        return True
    except:
        logging.error(f" No ARP traffic detected on {interface}")
        return False

# ===========================================================================================================
def process_arp_packet(packet):
    global my_ip, my_mask, target_network

    if packet[ARP].op == 1:
        logging.info(f"  ARP request received from: {packet[ARP].psrc}")
        target_network = ipaddress.ip_network(packet[ARP].psrc + "/24", strict=False)

        if target_network == ipaddress.ip_network('0.0.0.0/24'):
            logging.info(f"  ARP request received from invalid source network")
            monitor_arp_traffic()

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
    logging.info("")
    logging.info("Starting IP address configuration:")

    if my_ip is not None:
        try:
            logging.info(f"  Assigning IP address {my_ip}/{my_mask} to {interface}")
            command = f"ip addr add {my_ip}/{my_mask} dev {interface}"
            subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            logging.error(f" Cannot assign IP address: {e}")
            return False

# ===========================================================================================================
def check_internet_connection(host="45.33.32.156", port=80, timeout=3):
    logging.info("")
    logging.info("Checking for Internet connection:")

    socket.setdefaulttimeout(timeout)
    socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        socket.connect((host, port))
        logging.info("  Internet connection is available")
        return True
    except Exception as e:
        logging.error(" Internet connection is NOT available")
        return False

# ===========================================================================================================
def get_public_ip():
    try:
        response = requests.get('https://ifconfig.me/ip')

        if response.status_code == 200:
            logging.info(f"  Public IP address: {response.text}")
            return response.text
        else:
            logging.error("  Cannot get public IP address. Error in HTTP request")
            return False
    except Exception as e:
        logging.error(f" Cannot retrive public IP address: {str(e)}")
        return False

# ===========================================================================================================
def network_scan():
    global scan_file, my_ip

    logging.info("")
    logging.info(f"Starting network scan on subnet: {str(target_network)}")

    create_scan_file()

    net_scanner = nmap.PortScanner()
    target = str(target_network)
    options = "-sS -sV -O -p 1-1000"
    net_scanner.scan(target, arguments=options)

    # for host in net_scanner.all_hosts():
    #     with open(scan_file, 'w') as file:
    #         file.write(f"Host: {host} | {net_scanner[host].state()}")
    #         logging.info(f"  Host: {host} | {net_scanner[host].state()}")


    for host in net_scanner.all_hosts():
        logging.info(f"  Host: {host} ({net_scanner[host].hostname()})")
        logging.info("    State: ", net_scanner[host].state())
        logging.info("    OS: %s" % net_scanner[host]['osmatch'][0]['name'])
        for proto in net_scanner[host].all_protocols():
            logging.info("    Protocol: %s" % proto)
            ports = net_scanner[host][proto].keys()
            for port in ports:
                logging.info("    Port: %s\tState: %s\tService: %s\tVersion: %s" % (port, net_scanner[host][proto][port]['state'], net_scanner[host][proto][port]['name'], net_scanner[host][proto][port]['version']))

# ===========================================================================================================
def signal_handler(sig, frame):
    logging.info("")
    logging.info('You pressed Ctrl+C!')

    sys.exit(0)

# ===========================================================================================================
def cleanup():
    logging.info("")
    logging.info("Starting cleanup:")

    try:
        logging.info(f"  Removing IP address {my_ip} from interface {interface}")
        command = f"ip addr del {my_ip}/{my_mask} dev {interface}"
        subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL)
    except Exception as e:
        logging.error(f" Error removing IP address {my_ip} from interface {interface}: {e}")

    try:
        logging.info(f"  Disabling interface {interface}")
        command = f"ip link set dev {interface} arp off down"
        subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL)
    except Exception as e:
        logging.error(f" Error disabling interface {interface}: {e}")

    try:
        logging.info(f"  Restoring MAC Address on interface {interface}")
        command = f"macchanger -p {interface}"
        subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL)
    except Exception as e:
        logging.error(f" Error restoring MAC Address on interface {interface}: {e}")

    try:
        logging.info(f"  Deleting PID file {pid_file}")
        os.remove(pid_file)
    except Exception as e:
        logging.error(f" Error deleting PID file {pid_file}: {e}")
    
    logging.info("")
    logging.info(f"PI-SHARK execution ended")
    logging.info("===========================================================================================================")

# ===========================================================================================================
if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    logging.info("")
    logging.info("===========================================================================================================")
    logging.info(f"Starting PI-SHARK v{app_version}")

    if os.path.exists(pid_file):
        logging.error("PID file already exists. PI-Shark will be terminated.")
        sys.exit(1)

    main()