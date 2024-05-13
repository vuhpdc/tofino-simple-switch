import json
import os
import sys
import pprint
from netaddr import IPAddress, EUI

CONFIG_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
SWITCH_NAME = 's1'

with open(CONFIG_JSON, 'r') as f:
    data = json.load(f)
    if SWITCH_NAME not in data:
        print("Switch '%s' not found in switches.json file" % SWITCH_NAME)
        sys.exit(1)
    cfg = data[SWITCH_NAME]
    if "arp-resolver" not in cfg:
        cfg["arp-resolver"] = False

class color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# get a handle to the relevant tables
p4 = bfrt.switch.pipe
icmp = p4.Ingress.icmp_table
arp = p4.Ingress.arp_table
fw = p4.Ingress.forwarding_table

# perform static mapping of switch ports to hosts (or other switches)
# normally we would have the switch "learn" those, but for our purposes
# a static mapping is enough.
print(color.BOLD + "Configuring switch forwarding:" + color.END)
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

if cfg["arp-resolver"]:
    print(color.BOLD + "Configuring switch arp-resolver:" + color.END)

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


if endpoint:
    print(color.BOLD + "Configuring switch endpoint:" + color.END)
    err = None
    mac = EUI(cfg["endpoint"]['mac'])
    ip4 = IPAddress(cfg["endpoint"]['ip'])
    try:
        icmp.add_with_icmp_echo_response(dst_addr=ip4)
        arp.add_with_arp_resolve(dst_proto_addr=ip4, mac=mac)
    except Exception as e:
        err = e
    print("  %s / %s (%s)" % (mac, ip4, "ok" if err is None else err))
