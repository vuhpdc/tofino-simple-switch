#ifndef _PARSERS_P4
#define _PARSERS_P4

#include "types.p4"

parser TofinoIngressParser(packet_in P, out ingress_intrinsic_metadata_t IM) {
  state start {
    P.extract(IM);
    transition select(IM.resubmit_flag) {
      1 : parse_resubmit;
      0 : parse_port_metadata;
    }
  }

  state parse_resubmit { transition reject; }

  state parse_port_metadata {
    P.advance(PORT_METADATA_SIZE);
    transition accept;
  }
}

parser TofinoEgressParser(packet_in P, out egress_intrinsic_metadata_t IM) {
  state start {
    P.extract(IM);
    transition accept;
  }
}



parser IngressParser(packet_in P, out header_t H,
                     out metadata_t M,
                     out ingress_intrinsic_metadata_t IM) {
  TofinoIngressParser() TofinoParser;
  Checksum() ip_checksum;
  Checksum() icmp_checksum;

  bit<16> icmp_type_code;

  state start {
    // P.extract(IM);
    // P.advance(PORT_METADATA_SIZE);
    TofinoParser.apply(P, IM);
    transition parse_ethernet;
  }

  state parse_ethernet {
    P.extract(H.eth);
    transition select(H.eth.ether_type) {
        ETH_ARP  : parse_arp;
        ETH_IPV4 : parse_ip4;
         default : accept;
    }
  }

  state parse_arp {
    P.extract(H.arp);
    transition select(H.arp.hw_type, H.arp.proto_type) {
      (ARP_HTYPE_ETH, ARP_PTYPE_IP4) : parse_arp_ip4;
                             default : accept;
    }
  }

  state parse_arp_ip4 {
    P.extract(H.arp_ip4);
    transition accept;
  }

  state parse_ip4 {
    P.extract(H.ip4);
    ip_checksum.add(H.ip4);
    M.ip4_checksum_err = ip_checksum.verify();
    M.ip4_checksum_update = false;

    // parse IP packets with no options only
    // !! Currently we assume no fragmentation
    transition select(H.ip4.ihl, H.ip4.protocol) {
      (5, IP_ICMP) : parse_icmp;
           default : accept; }
  }

  state parse_icmp {
    // icmp_type_code = P.lookahead<bit<16>>();
    P.extract(H.icmp);
    icmp_checksum.subtract({H.icmp.checksum});
		icmp_checksum.subtract({H.icmp.msg_type, H.icmp.msg_code});
		icmp_checksum.subtract_all_and_deposit(M.icmp_checksum_tmp);
    transition accept;
  }
}

control IngressDeparser(packet_out P, inout header_t H,
                        in metadata_t M,
                        in ingress_intrinsic_metadata_for_deparser_t DIM) {

  Checksum() ip4_checksum;
  Checksum() icmp_checksum;

  apply {
    if (M.ip4_checksum_update) {
      H.ip4.hdr_checksum = ip4_checksum.update(
        { H.ip4.version,
          H.ip4.ihl,
          H.ip4.diffserv,
          H.ip4.total_len,
          H.ip4.identification,
          H.ip4.flags,
          H.ip4.frag_offset,
          H.ip4.ttl,
          H.ip4.protocol,
          H.ip4.src_addr,
          H.ip4.dst_addr } );
    }
    if (M.icmp_checksum_update) {
      H.icmp.checksum = icmp_checksum.update(
        {H.icmp.msg_type,
         H.icmp.msg_code,
         M.icmp_checksum_tmp});
    }
    P.emit(H);
  }
}

parser EgressParser(packet_in P,
                    out empty_header_t H,
                    out empty_metadata_t M,
                    out egress_intrinsic_metadata_t  IM) {
  state start {
    P.extract(IM);
    transition accept;
  }
}

control EgressDeparser(packet_out P,
                       inout empty_header_t H,
                       in empty_metadata_t M,
                       in egress_intrinsic_metadata_for_deparser_t DIM) {
  apply {
    P.emit(H);
  }
}

parser EmptyEgressParser(packet_in P, out empty_header_t H, out empty_metadata_t M,
                         out egress_intrinsic_metadata_t IM) {
  state start { transition accept; }
}

control EmptyEgressDeparser(packet_out pkt, inout empty_header_t H, in empty_metadata_t M,
                            in egress_intrinsic_metadata_for_deparser_t DIM) {
  apply {}
}


#endif
