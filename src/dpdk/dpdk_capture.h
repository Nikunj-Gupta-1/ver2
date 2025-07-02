/*
 * DPDK Packet Capture Library Header
 * Defines structures and function prototypes for high-performance packet capture
 */

#ifndef DPDK_CAPTURE_H
#define DPDK_CAPTURE_H

#include <stdint.h>
#include <rte_mbuf.h>

/* Maximum number of packets in a batch */
#define MAX_PKT_BURST 32
#define MAX_CORES 16

/* Packet structure for captured data */
struct packet {
    uint8_t *data;      /* Packet data pointer */
    uint16_t length;    /* Packet length */
    uint8_t port;       /* Port number */
    uint32_t timestamp; /* Capture timestamp */
};

/* Function prototypes */

/**
 * Initialize DPDK environment and configure packet capture
 * @param port DPDK port number
 * @param cores CPU cores to use (e.g., "0-1")
 * @param batch_size Maximum packets per batch
 * @return 0 on success, negative on error
 */
int dpdk_init(int port, const char *cores, int batch_size);

/**
 * Capture packets from the network interface
 * @param packets Array to store captured packets
 * @param max_packets Maximum number of packets to capture
 * @return Number of packets captured, negative on error
 */
int dpdk_capture_packets(struct packet *packets, int max_packets);

/**
 * Cleanup DPDK resources and shutdown
 */
void dpdk_cleanup(void);

/**
 * Get DPDK port statistics
 * @param port Port number
 * @param rx_packets Pointer to store received packet count
 * @param tx_packets Pointer to store transmitted packet count
 * @param rx_bytes Pointer to store received byte count
 * @param tx_bytes Pointer to store transmitted byte count
 * @return 0 on success, negative on error
 */
int dpdk_get_stats(int port, uint64_t *rx_packets, uint64_t *tx_packets,
                   uint64_t *rx_bytes, uint64_t *tx_bytes);

#endif /* DPDK_CAPTURE_H */
