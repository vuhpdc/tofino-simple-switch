#include <core.p4>
#include <tna.p4>

#include "parsers.p4"
#include "types.p4"

struct header_t {
  ethernet_h eth;
  arp_h arp;
  arp_ip4_h arp_ip4;
  ip4_h ip4;
  icmp_h icmp;
}

control SimpleSwitchIngress(inout header_t H, inout metadata_t M, in ingress_intrinsic_metadata_t IM,
                            in ingress_intrinsic_metadata_from_parser_t PIM,
                            inout ingress_intrinsic_metadata_for_deparser_t DIM,
                            inout ingress_intrinsic_metadata_for_tm_t TIM) {
  action reflect() {
    mac_addr_t tmp = H.eth.dst_addr;
    H.eth.dst_addr = H.eth.src_addr;
    H.eth.src_addr = tmp;
    TIM.drop_ctl = 0x0;
    TIM.ucast_egress_port = IM.ingress_port;
  }

  action forward(PortId_t port) {
    TIM.drop_ctl = 0x0;
    TIM.ucast_egress_port = port;
  }

  action drop() { TIM.drop_ctl[0:0] = 0x1; }

  table forwarding_table {
    key = {H.eth.dst_addr: exact;}
    actions = {ip_forward;drop;}
    size=1024
    default_action = drop()
  }

  action arp_resolve(mac_addr_t mac, ip4_addr_t ip4) {
    H.arp.opcode = ARP_RES;
    H.arp_ip4.dst_hw_addr = H.arp.src_hw_addr;
    H.arp_ip4.dst_proto_addr = H.arp.src_proto_addr;
    H.arp_ip4.src_hw_addr = mac;
    H.arp_ip4.src_proto_addr = ip4;
  }

  table arp_table {
    key = {H.arp_ip4.dst_proto_addr: exact;}
    actions = {arp_resolve;drop;}
    size=1024
    default_action = drop()
  }

  action icmp_echo_response() {
    H.icmp.msg_type = ICMP_ECHO_RES;
    H.icmp.checksum = 0;
  }

  table icmp_table {
    key = {H.ip4.dst_addr: exact;}
    actions = {icmp_echo_response; NoAction;}
    size = 1
    default_action = NoAction;
  }

  apply {
    if (H.arp_ip4.isValid() && H.arp.opcode == ARP_REQ)
      arp_table.apply();
    else if (H.icmp.isValid() && H.icmp.msg_type == ICMP_ECHO_REQ)
      icmp_table.apply();
    forwarding_table.apply();
  }
}



Pipeline(IngressParser(), SimpleSwitchIngress(), IngressDeparser(), EmptyEgressParser(), EmptyEgress(), EmptyEgressDeparser()) pipe;

Switch(pipe) main;
