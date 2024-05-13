import json
import os
import sys
import pprint
from netaddr import IPAddress, EUI

CONFIG_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
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
        print("Switch '%s' not found in switches.json file" % SWITCH_NAME)
        sys.exit(1)
    cfg = data[SWITCH_NAME]

# get a handle to the relevant tables
p4 = bfrt.switch.pipe
icmp = p4.Ingress.icmp_table
arp = p4.Ingress.arp_table
fw = p4.Ingress.forwarding_table

# perform static mapping of switch ports to hosts (or other switches)
# normally we would have the switch "learn" those, but for our purposes
# a static mapping is enough.
print(Color.BOLD + "Configuring switch forwarding:" + Color.END)
for p in cfg["ports"]:
    port = int(p)
    for i, h in enumerate(cfg["ports"][p]):
        err = None
        mac = EUI(h['mac'])
        try:
            fw.add_with_forward(dst_addr=mac, port=port)
        except Exception as e:
            err = e

        print("  %s %s (%s)" % (("port %d ->" % port) if i == 0 else " " * len("port %s ->" % p), mac, "ok" if err is None else err))

endpoint = "endpoint" in cfg and "mac" in cfg["endpoint"] and "ip" in cfg["endpoint"]

if endpoint:

    print(Color.BOLD + "Configuring switch endpoint:" + Color.END)
    err = None
    mac = EUI(cfg["endpoint"]['mac'])
    ip4 = IPAddress(cfg["endpoint"]['ip'])

    # Add an entry for the switch in the ICMP table
    try:
        icmp.add_with_icmp_echo_response(dst_addr=ip4)
    except Exception as e:
        err = e
    print("  %s / %s (%s)" % (mac, ip4, "ok" if err is None else err))


    if "arp-resolver" in cfg["endpoint"] and cfg["endpoint"]["arp-resolver"]:
        print(Color.BOLD + "Configuring switch arp-resolver:" + Color.END)

        # Add an ARP entry for the switch
        err = None
        try:
            arp.add_with_arp_resolve(dst_proto_addr=ip4, mac=mac)
        except Exception as e:
            err = e
        print("  %s -> %s (%s)" % (mac, ip4, "ok" if err is None else err))

        # Add ARP entries for each host
        for p in cfg["ports"]:
            port = int(p)
            for i, h in enumerate(cfg["ports"][p]):
                err = None
                ip4 = IPAddress(h['ip'])
                mac = EUI(h['mac'])
                try:
                    arp.add_with_arp_resolve(dst_proto_addr=ip4, mac=mac)
                except Exception as e:
                    err = e
                print("  %s -> %s (%s)" % (mac, ip4, "ok" if err is None else err))

