#ifndef _HEADERS_P4
#define _HEADERS_P4

struct header_t {
  ethernet_h eth;
  arp_h arp;
  arp_ip4_h arp_ip4;
  ip4_h ip4;
  icmp_h icmp;
}

struct metadata_t {
  bool ip4_checksum_err;
  bool ip4_checksum_update;
}

struct empty_header_t {}

struct empty_metadata_t {}

#endif