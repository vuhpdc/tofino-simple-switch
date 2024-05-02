tofino-simple-switch
--------------------

Program Tofino as a simple switch with basic forwarding based on destination MAC address.
The switch is also an ARP resolver. That is, it will answer ARP requests for given IPs or drop the packets when not known.
The switch also has MAC and IP addresses of its own, and will respond to ARP and ICMP requests for those addresses.