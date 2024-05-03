import json, os, sys
import pprint

from netaddr import IPAddress, EUI

SWITCHES_JSON = os.path.join(os.path.dirname(sys.argv[0]), "switches.json")
SWITCH_NAME = 's1'

with open(SWITCHES_JSON, 'r') as f:
    cfg = json.load(f)[SWITCH_NAME]


pprint.pprint(cfg)

p4 = bfrt.simple_switch.pipe
icmp = p4.SimpleSwitchIngress.icmp_table
arp = p4.SimpleSwitchIngress.arp_table
fw = p4.SimpleSwitchIngress.forwarding_table

# tell the switch the mac-ip mapping

switch_mac = EUI(cfg['mac'])
switch_ip  = IPAddress(cfg['ip'])
print(switch_ip)
icmp.add_with_icmp_echo_response(dst_addr=switch_ip)
arp.add_with_arp_resolve(dst_proto_addr=switch_ip,mac=switch_mac)

for p in cfg["ports"]:
    for h in cfg["ports"][p]:
        arp.add_with_arp_resolve(dst_proto_addr=IPAddress(h['ip']),mac=EUI(h['mac']))
        fw.add_with_forward(dst_addr=EUI(h['mac']),port=int(p))
