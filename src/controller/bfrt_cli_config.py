import json
import os
import sys
import pprint
from netaddr import IPAddress, EUI

CONFIG_JSON = "tofino2.json"
CONFIG_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_JSON)
SWITCH_NAME = 's1'

class Color:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

with open(CONFIG_JSON, 'r') as f:
    data = json.load(f)
    if SWITCH_NAME not in data:
        print("Switch '%s' not found in config.json" % SWITCH_NAME)
        sys.exit(1)
    cfg = data[SWITCH_NAME]

# get a handle to the relevant tables
P4 = bfrt.simple_switch.pipe
ICMP = P4.Ingress.icmp_table
ARP  = P4.Ingress.arp_table
FRWD = P4.Ingress.forwarding_table

# Configure the switch as an endpoint that can be pinged (ICMP)
# Additionally, if enabled it can be an ARP resolver as well
if "endpoint" in cfg and "mac" in cfg["endpoint"] and "ip" in cfg["endpoint"]:
    print(Color.BOLD + "Configuring switch endpoint:" + Color.END)

    err = None
    sw_mac = EUI(cfg["endpoint"]['mac'])
    sw_ip4 = IPAddress(cfg["endpoint"]['ip'])

    # Add an entry for the switch in the ICMP table
    try:
        ICMP.add_with_icmp_echo_response(dst_addr=sw_ip4)
    except Exception as e:
        err = e
    print("  %s / %s (%s)" % (sw_mac, sw_ip4, "ok" if err is None else err))


    if "arp-resolver" in cfg["endpoint"] and cfg["endpoint"]["arp-resolver"]:
        print(Color.BOLD + "Configuring switch arp-resolver:" + Color.END)

        # Add an ARP entry for the switch
        err = None
        try:
            ARP.add_with_arp_resolve(dst_proto_addr=sw_ip4, mac=sw_mac)
        except Exception as e:
            err = e
        print("  %s -> %s (%s)" % (sw_mac, sw_ip4, "ok" if err is None else err))

        # Add ARP entries for each host
        for p in cfg["ports"]:
            # port = int(p if '/' not in p else p.split('/')[0])
            # dp = int(p if '/' not in p else p.split('/')[1])

            for i, host_info in enumerate(cfg["ports"][p]):
                err = None
                ip4 = IPAddress(host_info['ip'])
                mac = EUI(host_info['mac'])
                try:
                    ARP.add_with_arp_resolve(dst_proto_addr=ip4, mac=mac)
                except Exception as e:
                    err = e
                print("  %s -> %s (%s)" % (mac, ip4, "ok" if err is None else err))

# perform static mapping of switch ports to hosts (or other switches)
# normally we would have the switch "learn" those, but for our purposes
# a static mapping is enough.
if "ports" in cfg:
    print(Color.BOLD + "Configuring switch forwarding:" + Color.END)
    for p in cfg["ports"]:
        port = int(p if '/' not in p else p.split('/')[0])
        dp = int(p if '/' not in p else p.split('/')[1])
        for i, host_info in enumerate(cfg["ports"][p]):
            err = None
            mac = EUI(host_info['mac'])
            try:
                FRWD.add_with_forward(dst_addr=mac, port=dp)
            except Exception as e:
                err = e

            port_or_indent = ("port %s ->" % p) if i == 0 else (" " * len("port %s ->" % p))
            print("  %s %s (%s)" % (port_or_indent, mac, "ok" if err is None else err))

