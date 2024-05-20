from p4utils.mininetlib.network_API import NetworkAPI
from p4utils_extra import *
import sys
import os
import json

if len(sys.argv) < 3:
    print("usage: python network.py SDE_PATH CFG_JSON")
    sys.exit(1)

SDE = os.path.abspath(sys.argv[1])
SDE_INSTALL = os.path.join(SDE, "install")
SRC = os.path.join(os.path.dirname(sys.argv[0]), "..", "..", "src")
# PROG = "switch.p4"
CFG = sys.argv[2]

if not os.path.exists(SDE):
    print("error: could not find Tofino SDE at '%s'" % SDE)
    sys.exit(1)
if not os.path.exists(SDE_INSTALL):
    print("error: could not find %s/install" % SDE)
    sys.exit(1)
if not os.path.exists(CFG):
    print("error: %s does not exists", CFG)
    sys.exit(1)

with open(CFG, 'r') as f:
    CFG = json.load(f)

import pprint

pprint.pprint(CFG)

net = NetworkAPI()

# Network general options
net.setLogLevel('info')
net.enableCli()

# Tofino compiler
# net.setCompiler(compilerClass=TF1_COMPILER if CFG['tofino'] == 1 else TF2_COMPILER,
#                 sde=SDE, sde_install=SDE_INSTALL)

# Make sure that all switches use the same compiler
# This is not fundamentally a problem, however P4Utils expects
# a single compiler for all switches and i can't bother patching it
CompilerClass = []
for sw in CFG:
    CompilerClass.append(Tofino1P4C if CFG[sw]['tofino'] == 1 else Tofino2P4C)
if len(set(CompilerClass)) > 1:
    print("Cannot have different Tofino compilers in different switches")
    sys.exit(1)
CompilerClass = CompilerClass[0]
net.setCompiler(compilerClass=CompilerClass, sde=SDE, sde_install=SDE_INSTALL)


# Network definition
for sw in CFG:
    # Add the switch
    net.addTofino(sw, sde=SDE, sde_install=SDE_INSTALL,
                  mac=CFG[sw]['endpoint']['mac'], ip=CFG[sw]['endpoint']['ip'],
                  cls=Tofino1 if CFG[sw]['tofino'] == 1 else Tofino2)
    net.setP4Source(sw, os.path.join(SRC, CFG[sw]['program']))

    # Add the hosts connected to the switch
    for p, nodes in CFG[sw]['ports'].items():
        # the config file assumes multiple nodes per port are possible
        # i don't think this is possible in minited/p4utils but better
        # keep the config like this for consistency with the real HW
        for node in nodes:
            if node['name'].startswith('s'):
                print("cannot connect with other switches at the moment")
                sys.exit(1)
            net.addHost(node['name'], ip=node['ip'])
            net.addLink(node['name'], sw, port2=int(p))
            net.setIntfMac(node['name'], sw, mac=node['mac'])



print("AAAAAAAAAAAAAAAAAAA", net.modules['comp']['class'])
# net.addTofino('s1', sde=SDE, sde_install=SDE_INSTALL,
#               mac="00:00:00:00:10:01", ip="10.10.10.1",
#               cls=Tofino1P4C if CFG['tofino'] == 1 else Tofino2P4C)
# net.setP4Source('s1', os.path.join(SRC, PROG))

# net.addHost('h1', ip="10.0.0.1")
# net.addLink('h1', 's1', port2=1 + (8 if tofino_ver == 2 else 0))
# net.setIntfMac('h1', 's1', mac="00:00:00:00:00:01")
# net.addHost('h2', ip="10.0.0.2")
# net.addLink('h2', 's1', port2=2 + (8 if tofino_ver == 2 else 0))
# net.setIntfMac('h2', 's1', mac="00:00:00:00:00:02")

# Nodes general options
net.enableLogAll()

# disable ARP table entries on hosts
#
# to handle ARP either the following should be enabled
# or the switch should act as an ARP resolver
# net.disableArpTables()

# Start the network
net.startNetwork()
