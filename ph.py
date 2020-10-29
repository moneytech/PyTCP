#!/usr/bin/env python3

"""

PyTCP, Python TCP/IP stack simulation version 0.1 - 2020, Sebastian Majewski
ph.py - protocol support for incoming and outgoing packets

"""

import time
import loguru
import threading

import ps_arp


class PacketHandler:
    """ Pick up and respond to incoming packets """

    from phrx_ether import phrx_ether
    from phrx_arp import phrx_arp
    from phrx_ip import phrx_ip
    from phrx_icmp import phrx_icmp
    from phrx_udp import phrx_udp
    from phrx_tcp import phrx_tcp
    from phrx_tcp import phrx_tcp_session

    from phtx_ether import phtx_ether
    from phtx_arp import phtx_arp
    from phtx_ip import phtx_ip
    from phtx_icmp import phtx_icmp
    from phtx_udp import phtx_udp
    from phtx_tcp import phtx_tcp

    def __init__(self, stack_mac_address, stack_ip_address, rx_ring, tx_ring, arp_cache):
        """ Class constructor """

        self.arp_probe_conflict_detected = False
        self.ip_address_claimed = False

        self.stack_mac_address = stack_mac_address
        self.stack_ip_address = stack_ip_address
        self.tx_ring = tx_ring
        self.rx_ring = rx_ring
        self.arp_cache = arp_cache
        self.logger = loguru.logger.bind(object_name="packet_handler.")

        self.tcp_sessions = {}

        # Update ARP cache object with reference to this packet handler so ARP cache can send out ARP requests
        self.arp_cache.packet_handler = self

        threading.Thread(target=self.__packet_handler).start()
        self.logger.debug("Started packet handler")

        # Send three ARP probes to test if there is any IP address conflict
        for i in range(3):
            self.__send_arp_probe()
            self.logger.debug(f"Sent out ARP probe {i} for {self.stack_ip_address}")
            time.sleep(1)
            if self.arp_probe_conflict_detected:
                self.logger.warning(f"Unable to claim IP address {self.stack_ip_address}, stack IP operations will not be performed")
                return

        self.__send_arp_announcement()
        self.ip_address_claimed = True
        self.logger.debug(f"Sent out ARP annoucement for {self.stack_ip_address}")

        time.sleep(1)
        self.__send_gratitous_arp()
        self.logger.debug(f"Sent out gratitous ARP for {self.stack_ip_address}")

    def __send_arp_probe(self):
        """ Send out ARP probe to detect possible IP conflict """

        self.phtx_arp(
            ether_src=self.stack_mac_address,
            ether_dst="ff:ff:ff:ff:ff:ff",
            arp_oper=ps_arp.ARP_OP_REQUEST,
            arp_sha=self.stack_mac_address,
            arp_spa="0.0.0.0",
            arp_tha="00:00:00:00:00:00",
            arp_tpa=self.stack_ip_address,
        )

    def __send_arp_announcement(self):
        """ Send out ARP announcement to claim IP address """

        self.phtx_arp(
            ether_src=self.stack_mac_address,
            ether_dst="ff:ff:ff:ff:ff:ff",
            arp_oper=ps_arp.ARP_OP_REQUEST,
            arp_sha=self.stack_mac_address,
            arp_spa=self.stack_ip_address,
            arp_tha="00:00:00:00:00:00",
            arp_tpa=self.stack_ip_address,
        )

    def __send_gratitous_arp(self):
        """ Send out gratitous arp """

        self.phtx_arp(
            ether_src=self.stack_mac_address,
            ether_dst="ff:ff:ff:ff:ff:ff",
            arp_oper=ps_arp.ARP_OP_REPLY,
            arp_sha=self.stack_mac_address,
            arp_spa=self.stack_ip_address,
            arp_tha="00:00:00:00:00:00",
            arp_tpa=self.stack_ip_address,
        )

    def __packet_handler(self):
        """ Thread that picks up incoming packets from RX ring and process them """

        while True:
            self.phrx_ether(self.rx_ring.dequeue())
