#ifndef STRAGGLEML_P4_UTIL_P4
#define STRAGGLEML_P4_UTIL_P4

parser TofinoIngressParser(packet_in P, out ingress_intrinsic_metadata_t IM) {
  state start {
    pkt.extract(IM);
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
    pkt.extract(eg_intr_md);
    transition accept;
  }
}

struct empty_header_t {}

struct empty_metadata_t {}

parser EmptyEgressParser(packet_in P, out empty_header_t H, out empty_metadata_t M,
                         out egress_intrinsic_metadata_t IM) {
  state start { transition accept; }
}

control EmptyEgressDeparser(packet_out pkt, inout empty_header_t H, in empty_metadata_t M,
                            in egress_intrinsic_metadata_for_deparser_t DIM) {
  apply {}
}

control EmptyEgress(inout empty_header_t H, inout empty_metadata_t M, in egress_intrinsic_metadata_t IM,
                    in egress_intrinsic_metadata_from_parser_t PIM,
                    inout egress_intrinsic_metadata_for_deparser_t DIM,
                    inout egress_intrinsic_metadata_for_output_port_t OPIM) {
  apply {}
}

#endif