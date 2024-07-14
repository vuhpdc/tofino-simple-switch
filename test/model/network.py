import pprint
from p4utils.mininetlib.network_API import NetworkAPI
from p4utils_extra import *
import sys
import os
import json

if len(sys.argv) < 3:
    print("usage: python network.py <SDE> <CONFIG>")
    sys.exit(1)

SDE = sys.argv[1]
SDE_INSTALL = os.path.join(SDE, "install")
ROOT = os.path.join(os.path.dirname(sys.argv[0]), "..", "..")
CFG = os.path.abspath(sys.argv[2])

if not os.path.exists(SDE):
    print("error: could not find Tofino SDE at '%s'" % SDE)
    sys.exit(1)
if not os.path.exists(SDE_INSTALL):
    print("error: could not find %s/install" % SDE)
    sys.exit(1)
if not os.path.exists(CFG):
    print("error: %s does not exists" % CFG)
    sys.exit(1)

with open(CFG, 'r') as f:
    CFG = json.load(f)


pprint.pprint(CFG)

net = NetworkAPI()

# Network general options
net.setLogLevel('info')

# Make sure that all switches use the same compiler
# This is not fundamentally a problem, however P4Utils expects
# a single compiler for all switches and i can't bother patching it
CompilerClass = []
for sw in CFG:
    CompilerClass.append(Tofino1P4C if CFG['tofino'] == 1 else Tofino2P4C)
if len(set(CompilerClass)) > 1:
    print("Cannot have different Tofino compilers in different switches")
    sys.exit(1)
CompilerClass = CompilerClass[0]
net.setCompiler(compilerClass=CompilerClass, sde=SDE, sde_install=SDE_INSTALL)

# Network definition
sw = CFG['name']

# Add the switch
net.addTofino(sw, sde=SDE, sde_install=SDE_INSTALL,
              #mac=CFG['endpoint']['mac'], ip=CFG['endpoint']['ip4'],
              cls=Tofino1 if CFG['tofino'] == 1 else Tofino2)
net.setP4Source(sw, os.path.join(ROOT, CFG['program']))

# Add the hosts and connect them to the switch
for p, info in CFG['ports'].items():
    if info['to']['kind'] != "host":
        print("can only connect with hosts at the moment!")
        sys.exit(1)
    h = info['to']
    port = int(p.split('/')[0]) if '/' in p else int(p)
    port = 4 * (port - 1)
    host = net.addHost(h['name'], ip=h['ip4'])
    net.addLink(h['name'], sw, port2=port)
    net.setIntfMac(h['name'], sw, h['mac'])
    net.setIntfIp(h['name'], sw, "%s/%s" % (h['ip4'], h['prefix']))
    net.setIntfName(h['name'], sw, h['iface'])

# General options
net.enableLogAll()

# disable ARP table entries on hosts
#
# to handle ARP either the following should be enabled
# or the switch should act as an ARP resolver
# net.disableArpTables()

# Start the network
net.disableCli()
net.startNetwork()

# Insert ip routes for the switch endpoint(s)
# We can only do this after the network has started
for p, info in CFG['ports'].items():
    if info['to']['kind'] != "host":
        continue
    h = info['to']
    for e in CFG['endpoints']:
        if e['enabled']:
            route_cmd = "sudo ip route add %s dev %s" % (e['ip4'], h['iface'])
            arp_cmd = "arp -s %s %s" % (e['ip4'], e['mac'])
            print("%s: %s" % (h['name'], route_cmd))
            net.net.get(h['name']).cmd(route_cmd)

net.start_net_cli()
