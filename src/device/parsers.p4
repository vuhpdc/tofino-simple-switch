#ifndef STRAGGLEML_APP_P4_PARSERS
#define STRAGGLEML_APP_P4_PARSERS

#include "types.p4"

parser IngressParser(packet_in P, out header_t H,
                     out ingress_metadata_t M,
                     out ingress_intrinsic_metadata_t IM) {
  TofinoIngressParser() TofinoParser;
  Checksum() ip_checksum;
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
    M.ip.setValid();
    M.ip.checksum_err = ip_checksum.verify();
    M.ip.checksum_update = true;

    // parse IP packets with no options only
    // !! Currently we assume no fragmentation
    transition select(H.ip4.ihl, H.ip4.protocol) {
      (5, IP_ICMP) : parse_icmp;
           default : accept; }
  }

  state parse_icmp {
    P.extract(H.icmp);
    transition accept;
  }
}

control IngressDeparser(packet_out P, inout header_t H,
                        in ingress_metadata_t M,
                        in ingress_intrinsic_metadata_for_deparser_t DIM) {

  Checksum() ip4_checksum;

  apply {
    if (M.ip.checksum_update) {
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
    P.emit(M.bridge); // Add bridge metadata
    P.emit(H);
  }
}

parser EgressParser(packet_in P, out header_t H,
                    out egress_metadata_t M,
                    out egress_intrinsic_metadata_t IM) {

  state start {
    P.extract(IM);
    P.extract(M.bridge);
    transition select(M.bridge.is_ml_packet) {
       true : parse_ml;
      false : accept;
    }
  }
  state parse_ml {
    P.extract(M.ml);
    transition accept;
  }
}

control EgressDeparser(packet_out P, inout header_t H,
                       in egress_metadata_t M,
                       in egress_intrinsic_metadata_for_deparser_t DIM) {

    Checksum() ip4_checksum;

    apply {
      if (M.ip.checksum_update) {
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
      P.emit(H);
    }
}

#endif