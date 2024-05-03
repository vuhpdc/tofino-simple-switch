from p4utils.utils.compiler import BF_P4C
from p4utils.mininetlib.network_API import NetworkAPI

import sys
import os

SDE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else \
    (os.path.abspath(os.environ['SDE']) if 'SDE' in os.environ else "")
SDE_INSTALL = os.path.join(SDE, "install")
SRC = os.path.join(os.path.dirname(sys.argv[0]), "..", "..", "src", "device")
PROG = "simple_switch.p4"

if not os.path.exists(SDE_INSTALL):
    print("Could not find Tofino SDE at '%s'. Exiting..." % SDE_INSTALL)
    sys.exit(1)

net = NetworkAPI()

# Network general options
net.setLogLevel('info')
net.enableCli()

# Tofino compiler
net.setCompiler(compilerClass=BF_P4C, sde=SDE, sde_install=SDE_INSTALL)

# Network definition
net.addTofino('s1', sde=SDE, sde_install=SDE_INSTALL, mac="00:00:00:00:10:01", ip="10.10.10.1")
net.setP4Source('s1', os.path.join(SRC, PROG))

# net.addTofino('s2', sde=SDE, sde_install=SDE_INSTALL)
net.addHost('h1', ip="10.0.0.1")
net.addLink('h1', 's1', port2=1)
net.setIntfMac('h1', 's1', mac="00:00:00:00:00:01")

net.addHost('h2', ip="10.0.0.2")
net.addLink('h2', 's1', port2=2)
net.setIntfMac('h2', 's1', mac="00:00:00:00:00:02")

# Nodes general options
net.enableLogAll()

# Start the network
net.startNetwork()

# net.getNode('h1').defaultIntf().setMAC("00:00:00:00:01:01")