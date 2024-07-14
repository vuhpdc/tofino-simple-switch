#include <core.p4>
#include <tna.p4>

#include "parsers.p4"
#include "types.p4"

control Ingress(inout header_t H, inout metadata_t M,
                in ingress_intrinsic_metadata_t IM,
                in ingress_intrinsic_metadata_from_parser_t PIM,
                inout ingress_intrinsic_metadata_for_deparser_t DIM,
                inout ingress_intrinsic_metadata_for_tm_t TIM) {

  action reflect() {
    mac_addr_t tmp = H.eth.dst_addr;
    H.eth.dst_addr = H.eth.src_addr;
    H.eth.src_addr = tmp;
    DIM.drop_ctl = 0x0;
  }

  action forward(PortId_t port) {
    DIM.drop_ctl = 0x0;
    TIM.ucast_egress_port = port;
    TIM.bypass_egress = 1w1;
  }

  action drop() { DIM.drop_ctl[0:0] = 0x1; }

  action multicast(MulticastGroupId_t mgid) {
    // mgid 1 is the mgid of ALL active ports
    TIM.mcast_grp_a = mgid;
    TIM.level1_exclusion_id = (bit<16>) IM.ingress_port;
    //We use 0x8000 + dev_port as the RID and XID for the flood group
    //TIM.level1_exclusion_id = 7w0b1000000 ++ TIM.ingress_port;
    TIM.bypass_egress = 1w1;
    DIM.drop_ctl[0:0] = 0;
  }

  table forwarding_table {
    key = {H.eth.dst_addr: exact;}
    actions = {forward;multicast;drop;}
    size=1024;
    // The default_action is controller by config.json
    default_action = multicast(1);
  }

  action arp_resolve(mac_addr_t mac) {
    H.arp.opcode = ARP_RES;

    H.arp_ip4.dst_hw_addr = H.arp_ip4.src_hw_addr;
    H.arp_ip4.src_hw_addr = mac;

    ip4_addr_t tmp1 = H.arp_ip4.dst_proto_addr;
    H.arp_ip4.dst_proto_addr = H.arp_ip4.src_proto_addr;
    H.arp_ip4.src_proto_addr = tmp1;

    H.eth.dst_addr = H.eth.src_addr;
    H.eth.src_addr = mac;
  }

  table arp_table {
    key = {H.arp_ip4.dst_proto_addr: exact;}
    actions = {arp_resolve;NoAction;}
    size = 1024;
    default_action = NoAction;
  }

  action icmp_echo_response() {
    // swap mac addresses
    mac_addr_t tmp2 = H.eth.src_addr;
    H.eth.src_addr = H.eth.dst_addr;
    H.eth.dst_addr = tmp2;

    // swap ip addresses
    ip4_addr_t tmp = H.ip4.src_addr;
    H.ip4.src_addr = H.ip4.dst_addr;
    H.ip4.dst_addr = tmp;

    H.icmp.msg_type = ICMP_ECHO_RES;
    // H.icmp.checksum = 0;
    M.ip4_checksum_update = true;
    M.icmp_checksum_update = true;
  }

  table icmp_table {
    key = {H.ip4.dst_addr: exact;}
    actions = {icmp_echo_response; NoAction;}
    size = 1;
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

control EmptyEgress(inout empty_header_t H, inout empty_metadata_t M,
                    in egress_intrinsic_metadata_t IM,
                    in egress_intrinsic_metadata_from_parser_t PIM,
                    inout egress_intrinsic_metadata_for_deparser_t DIM,
                    inout egress_intrinsic_metadata_for_output_port_t OPIM) {
  apply {}
}

Pipeline(IngressParser(), Ingress(), IngressDeparser(), EgressParser(), EmptyEgress(), EgressDeparser()) pipe;

Switch(pipe) main;
