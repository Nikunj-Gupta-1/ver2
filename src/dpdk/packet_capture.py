"""
Python wrapper for DPDK packet capture library.
Provides a clean Python interface to the DPDK C library.
"""

import ctypes
import os
import logging
from ctypes import Structure, c_uint8, c_uint16, c_uint32, c_void_p, POINTER

# Packet structure matching C definition
class Packet(Structure):
    _fields_ = [
        ("data", POINTER(c_uint8)),
        ("length", c_uint16),
        ("port", c_uint8),
        ("timestamp", c_uint32)
    ]

class DPDKPacketCapture:
    def __init__(self, port=0, cores="0", batch_size=32):
        self.port = port
        self.cores = cores
        self.batch_size = batch_size
        self.lib = None
        self.initialized = False
        self.logger = logging.getLogger(__name__)
        
    def initialize(self):
        """Initialize DPDK library and configure packet capture."""
        try:
            # Load the DPDK capture library
            lib_path = "./libdpdk_capture.so"
            if not os.path.exists(lib_path):
                lib_path = "/usr/local/lib/libdpdk_capture.so"
                
            if not os.path.exists(lib_path):
                self.logger.error("DPDK capture library not found. Run 'make' to build it.")
                return False
                
            self.lib = ctypes.CDLL(lib_path)
            
            # Define function signatures
            self.lib.dpdk_init.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
            self.lib.dpdk_init.restype = ctypes.c_int
            
            self.lib.dpdk_capture_packets.argtypes = [POINTER(Packet), ctypes.c_int]
            self.lib.dpdk_capture_packets.restype = ctypes.c_int
            
            self.lib.dpdk_cleanup.argtypes = []
            self.lib.dpdk_cleanup.restype = None
            
            # Initialize DPDK
            cores_bytes = self.cores.encode('utf-8')
            result = self.lib.dpdk_init(self.port, cores_bytes, self.batch_size)
            
            if result != 0:
                self.logger.error(f"DPDK initialization failed with error code: {result}")
                return False
                
            self.initialized = True
            self.logger.info(f"DPDK initialized successfully on port {self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize DPDK: {e}")
            return False
            
    def capture_packets(self):
        """Capture a batch of packets from the network interface."""
        if not self.initialized:
            self.logger.error("DPDK not initialized")
            return []
            
        try:
            # Allocate packet buffer
            packet_buffer = (Packet * self.batch_size)()
            
            # Capture packets
            num_packets = self.lib.dpdk_capture_packets(packet_buffer, self.batch_size)
            
            if num_packets < 0:
                self.logger.error("Packet capture failed")
                return []
                
            # Convert C packets to Python dictionaries
            packets = []
            for i in range(num_packets):
                packet = packet_buffer[i]
                
                # Copy packet data
                data = ctypes.string_at(packet.data, packet.length)
                
                packet_dict = {
                    'data': data,
                    'length': packet.length,
                    'port': packet.port,
                    'timestamp': packet.timestamp
                }
                
                packets.append(packet_dict)
                
            return packets
            
        except Exception as e:
            self.logger.error(f"Error capturing packets: {e}")
            return []
            
    def cleanup(self):
        """Cleanup DPDK resources."""
        if self.lib and self.initialized:
            try:
                self.lib.dpdk_cleanup()
                self.initialized = False
                self.logger.info("DPDK cleanup completed")
            except Exception as e:
                self.logger.error(f"Error during DPDK cleanup: {e}")
                
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()
