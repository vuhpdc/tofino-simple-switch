import json
import os
import sys
import pprint
from netaddr import IPAddress, EUI
from collections import OrderedDict

CONFIG_JSON = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "config.json"))

config_txt = os.path.join(os.path.dirname(__file__), 'config.txt')
if os.path.exists(config_txt):
    with open(config_txt, 'r') as f:
        CONFIG_JSON = f.read().strip()

print("\nUsing config:\n  %s\n" % CONFIG_JSON)


class Color:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


with open(CONFIG_JSON, 'r') as f:
    cfg = json.load(f)

SWITCH_NAME = cfg['name']

# get a handle to the relevant tables
P4 = bfrt.simple_switch.pipe
ICMP = P4.Ingress.icmp_table
ARP = P4.Ingress.arp_table
FRWD = P4.Ingress.forwarding_table

err = None


def get_cage_channel_pair(p):
    return (int(p.split('/')[0]), int(p.split('/')[1])) if '/' in p else (int(p), 0)


print(Color.BOLD + "Configuring switch:" + Color.END)
print("  Tofino%d (%s)" % (cfg['tofino'], "asic" if cfg['asic'] else "model"))

# ****************************************************************************#
# * Cleanup any previous configurations
# ****************************************************************************#
print(Color.BOLD + "Cleaning up previous configurations:" + Color.END)

cleanup_commands = [
    {'cmd': "bfrt.simple_switch.pipe.clear()", 'asic-only': False},
    {'cmd': "bfrt.port.port.clear()", 'asic-only': True}
]

for c in cleanup_commands:
    # err = None
    try:
        err = "n/a" if c['asic-only'] and not cfg['asic'] else exec(c['cmd'])
    except Exception as e:
        err = e
    print("  %s (%s)" % (c['cmd'], err if err else "ok"))


for p in cfg['ports']:
    cage, channel = get_cage_channel_pair(p)
    entry = bfrt.port.port_hdl_info.get(
        CONN_ID=cage, CHNL_ID=channel, print_ents=False)
    if isinstance(entry, int) and dev_port < 0:
        print("ERROR: Could not find DEV_PORT for '%s'" % p)
        exit
    cfg['ports'][p]['cage'] = cage
    cfg['ports'][p]['channel'] = channel
    cfg['ports'][p]['dev_port'] = entry.data[b'$DEV_PORT']

    # PORTS[p] = {'cage': cage, 'channel': channel,
    #             'dev_port': port.data[b'$DEV_PORT']}

PORTS = cfg['ports']
DEV_PORTS = [p['dev_port'] for _, p in PORTS.items()]

# ****************************************************************************#
# * Configure ports
# ****************************************************************************#
print(Color.BOLD + "Configuring ports:" + Color.END)

if cfg['asic']:
    for _, p in PORTS.items():
        err = None
        try:
            # The following is equivalent to the port manager (pm) sequence:
            #   port-add cage/- 100G None
            #   an-set cage/- 2
            #   port-enb cage/-
            bfrt.port.port.add(DEV_PORT=p['dev_port'], SPEED="BF_SPEED_%sG" % p['speed'],
                               FEC="BF_FEC_TYP_NONE", PORT_ENABLE=p['enabled'],
                               AUTO_NEGOTIATION="PM_AN_FORCE_%s" % ("ENABLE" if p['auto-negotiation'] else "DISABLE"))
        except Exception as e:
            err = e
        print("  %d/%d -> %d (%s)" %
              (p['cage'], p['channel'], p['dev_port'], err if err else "ok"))
else:
    print("  skipping in model mode")

# ****************************************************************************#
# * Adding multicast group(s)
# ****************************************************************************#
print(Color.BOLD + "Creating multicast group(s):" + Color.END)

MGID_ALL_PORTS = 1

cfg['multicast'][str(MGID_ALL_PORTS)] = {
    'ports': cfg['ports'].keys(), 'desc': "broadcast to all ports"}
cfg['multicast'] = OrderedDict(sorted(cfg['multicast'].items()))

mgid = MGID_ALL_PORTS
node_id = 1
replication_id = 1

for mc in cfg['multicast']:
    err = None
    ports = [PORTS[p]['dev_port'] for p in cfg['multicast'][mc]['ports']]
    try:
        # try:
        bfrt.pre.node.entry(MULTICAST_NODE_ID=node_id, MULTICAST_RID=replication_id,
                            MULTICAST_LAG_ID=[], DEV_PORT=ports).push()
        # the following line is equivalent to the one above
        #   bfrt.pre.node.add(node_id, replication_id, [], mc['ports'])
        bfrt.pre.mgid.add(MGID=mgid, MULTICAST_NODE_ID=[node_id],
                          MULTICAST_NODE_L1_XID_VALID=[False],
                          MULTICAST_NODE_L1_XID=[0])
    except Exception as e:
        err = e

    mgid += 1
    node_id += 1
    replication_id += 1
    # except Exception as e:
    #     err = e
    print("  %d -> %s [%s] (%s)" % (int(mc), ','.join(map(str, ports)),
           cfg['multicast'][mc]['desc'], err if err else "ok"))

# ****************************************************************************#
# * Configure the forwarding table
# ****************************************************************************#
print(Color.BOLD + "Configuring forwarding:" + Color.END)

# Add entries for each host port
for _, p in cfg['ports'].items():
    if p['to']['kind'] == 'host':
        err = None
        mac = EUI(p['to']['mac'])
        port = p['dev_port']
        try:
            FRWD.add_with_forward(dst_addr=mac, port=port)
        except Exception as e:
            err = e
        print("  %s -> port %3d (%s)" % (mac, port, err if err else "ok"))

MGID_ALL_PORTS = 1  # we will create it after configuring the forwarding table

# Add the broadcast entry ff:ff...
err = None
mac = EUI('ff:ff:ff:ff:ff:ff')
try:
    FRWD.add_with_multicast(dst_addr=mac, mgid=MGID_ALL_PORTS)
except Exception as e:
    err = e
print("  %s -> mgid %3d (%s)" % (mac, MGID_ALL_PORTS, err if err else 'ok'))

# Configure the miss behavior
err = None
try:
    if cfg['drop-on-miss']:
        FRWD.set_default_with_drop()
    else:
        FRWD.set_default_with_multicast(mgid=MGID_ALL_PORTS)
except Exception as e:
    err = e

print("               miss -> %s (%s)" %
      ("drop" if cfg['drop-on-miss'] else ("multicast(%d)" % (MGID_ALL_PORTS)), err if err else 'ok'))


# ****************************************************************************#
# * Configure ARP table
# ****************************************************************************#
print(Color.BOLD + "Configuring switch ARP resolver:" + Color.END)

arp_entries = len(cfg['ports']) + \
    len([e for e in cfg['endpoints'] if e['enabled']])

if cfg['arp-resolver']:
    for _, p in cfg['ports'].items():
        err = None
        mac = EUI(p['to']['mac'])
        ip4 = IPAddress(p['to']['ip4'])
        try:
            ARP.add_with_arp_resolve(dst_proto_addr=ip4, mac=mac)
        except Exception as e:
            err = e
        print("  %s -> %s (%s)" % (ip4, mac, err if err else "ok"))

# even if not an ARP resolver, the switch should be able to respond
# to ARP requests for its own IP endpoints
for e in [e for e in cfg['endpoints'] if e['enabled']]:
    err = None
    mac = EUI(e['mac'])
    ip4 = IPAddress(e['ip4'])
    try:
        ARP.add_with_arp_resolve(dst_proto_addr=ip4, mac=mac)
    except Exception as e:
        err = e
    print("  %s -> %s [switch-endpoint] (%s)" %
          (ip4, mac, err if err else "ok"))

if arp_entries == 0:
    print("  n/a")

# ****************************************************************************#
# * Configure ICMP table
# ****************************************************************************#
print(Color.BOLD + "Configuring switch ICMP endpoint(s):" + Color.END)

cnt = len([e for e in cfg['endpoints'] if e['enabled']])

for e in cfg['endpoints']:
    err = None
    if e['enabled']:
        ip4 = IPAddress(e['ip4'])
        try:
            ICMP.add_with_icmp_echo_response(dst_addr=ip4)
        except Exception as e:
            err = e
        print("  %s (%s)" % (ip4, err if err else "ok"))

if cnt == 0:
    print("  n/a")
