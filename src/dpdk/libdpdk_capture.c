/*
 * DPDK Packet Capture Library Implementation
 * High-performance packet capture using DPDK kernel-bypass technology
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>

#include <rte_common.h>
#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#include <rte_mempool.h>
#include <rte_cycles.h>

#include "dpdk_capture.h"

/* Global variables */
static struct rte_mempool *mbuf_pool = NULL;
static int g_port_id = 0;
static int g_batch_size = MAX_PKT_BURST;
static volatile sig_atomic_t force_quit = 0;

/* Port configuration */
static const struct rte_eth_conf port_conf_default = {
    .rxmode = {
        .max_lro_pkt_size = RTE_ETHER_MAX_LEN,
    },
};

static void signal_handler(int signum)
{
    if (signum == SIGINT || signum == SIGTERM) {
        printf("\nSignal %d received, preparing to exit...\n", signum);
        force_quit = 1;
    }
}

static int port_init(uint16_t port, struct rte_mempool *mbuf_pool)
{
    struct rte_eth_conf port_conf = port_conf_default;
    const uint16_t rx_rings = 1, tx_rings = 1;
    uint16_t nb_rxd = 1024;
    uint16_t nb_txd = 1024;
    int retval;
    uint16_t q;
    struct rte_eth_dev_info dev_info;
    struct rte_eth_txconf txconf;

    if (!rte_eth_dev_is_valid_port(port))
        return -1;

    retval = rte_eth_dev_info_get(port, &dev_info);
    if (retval != 0) {
        printf("Error during getting device (port %u) info: %s\n",
                port, strerror(-retval));
        return retval;
    }

    if (dev_info.tx_offload_capa & RTE_ETH_TX_OFFLOAD_MBUF_FAST_FREE)
        port_conf.txmode.offloads |= RTE_ETH_TX_OFFLOAD_MBUF_FAST_FREE;

    /* Configure the Ethernet device. */
    retval = rte_eth_dev_configure(port, rx_rings, tx_rings, &port_conf);
    if (retval != 0)
        return retval;

    retval = rte_eth_dev_adjust_nb_rx_tx_desc(port, &nb_rxd, &nb_txd);
    if (retval != 0)
        return retval;

    /* Allocate and set up 1 RX queue per Ethernet port. */
    for (q = 0; q < rx_rings; q++) {
        retval = rte_eth_rx_queue_setup(port, q, nb_rxd,
                rte_eth_dev_socket_id(port), NULL, mbuf_pool);
        if (retval < 0)
            return retval;
    }

    txconf = dev_info.default_txconf;
    txconf.offloads = port_conf.txmode.offloads;
    /* Allocate and set up 1 TX queue per Ethernet port. */
    for (q = 0; q < tx_rings; q++) {
        retval = rte_eth_tx_queue_setup(port, q, nb_txd,
                rte_eth_dev_socket_id(port), &txconf);
        if (retval < 0)
            return retval;
    }

    /* Start the Ethernet port. */
    retval = rte_eth_dev_start(port);
    if (retval < 0)
        return retval;

    /* Display the port MAC address. */
    struct rte_ether_addr addr;
    retval = rte_eth_macaddr_get(port, &addr);
    if (retval != 0)
        return retval;

    printf("Port %u MAC: %02x:%02x:%02x:%02x:%02x:%02x\n",
            port, RTE_ETHER_ADDR_BYTES(&addr));

    /* Enable RX in promiscuous mode for the Ethernet device. */
    retval = rte_eth_promiscuous_enable(port);
    if (retval != 0)
        return retval;

    return 0;
}

int dpdk_init(int port, const char *cores, int batch_size)
{
    int argc = 0;
    char *argv[10];
    char core_arg[64];
    char app_name[] = "dpdk_capture";
    
    /* Setup arguments for DPDK EAL */
    argv[argc++] = app_name;
    argv[argc++] = "-l";
    
    snprintf(core_arg, sizeof(core_arg), "%s", cores);
    argv[argc++] = core_arg;
    
    argv[argc++] = "--";
    argv[argc] = NULL;

    /* Initialize the Environment Abstraction Layer (EAL) */
    int ret = rte_eal_init(argc, argv);
    if (ret < 0) {
        printf("Error with EAL initialization\n");
        return -1;
    }

    /* Check that there is at least one port available */
    unsigned nb_ports = rte_eth_dev_count_avail();
    if (nb_ports == 0) {
        printf("Error: no Ethernet ports available\n");
        rte_eal_cleanup();
        return -2;
    }

    /* Validate port number */
    if (port >= nb_ports) {
        printf("Error: port %d not available (only %u ports)\n", port, nb_ports);
        rte_eal_cleanup();
        return -3;
    }

    g_port_id = port;
    g_batch_size = (batch_size > 0 && batch_size <= MAX_PKT_BURST) ? batch_size : MAX_PKT_BURST;

    /* Create packet buffer pool */
    mbuf_pool = rte_pktmbuf_pool_create("MBUF_POOL", 8192,
        250, 0, RTE_MBUF_DEFAULT_BUF_SIZE, rte_socket_id());

    if (mbuf_pool == NULL) {
        printf("Error: cannot create mbuf pool\n");
        rte_eal_cleanup();
        return -4;
    }

    /* Initialize port */
    if (port_init(g_port_id, mbuf_pool) != 0) {
        printf("Error: cannot init port %d\n", g_port_id);
        rte_eal_cleanup();
        return -5;
    }

    /* Install signal handlers */
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    printf("DPDK initialized successfully on port %d\n", g_port_id);
    return 0;
}

int dpdk_capture_packets(struct packet *packets, int max_packets)
{
    struct rte_mbuf *bufs[MAX_PKT_BURST];
    uint16_t nb_rx;
    int i;
    uint32_t timestamp;

    if (!packets || max_packets <= 0) {
        return -1;
    }

    /* Limit to our batch size */
    int capture_count = (max_packets < g_batch_size) ? max_packets : g_batch_size;

    /* Receive packets */
    nb_rx = rte_eth_rx_burst(g_port_id, 0, bufs, capture_count);

    if (nb_rx == 0) {
        return 0; /* No packets received */
    }

    /* Get current timestamp */
    timestamp = (uint32_t)(rte_get_tsc_cycles() / rte_get_tsc_hz());

    /* Process received packets */
    for (i = 0; i < nb_rx; i++) {
        struct rte_mbuf *mbuf = bufs[i];
        
        packets[i].data = rte_pktmbuf_mtod(mbuf, uint8_t*);
        packets[i].length = rte_pktmbuf_data_len(mbuf);
        packets[i].port = g_port_id;
        packets[i].timestamp = timestamp;
    }

    /* Free mbufs after copying data */
    for (i = 0; i < nb_rx; i++) {
        rte_pktmbuf_free(bufs[i]);
    }

    return nb_rx;
}

int dpdk_get_stats(int port, uint64_t *rx_packets, uint64_t *tx_packets,
                   uint64_t *rx_bytes, uint64_t *tx_bytes)
{
    struct rte_eth_stats stats;
    int ret;

    if (port != g_port_id) {
        return -1;
    }

    ret = rte_eth_stats_get(port, &stats);
    if (ret != 0) {
        return ret;
    }

    if (rx_packets) *rx_packets = stats.ipackets;
    if (tx_packets) *tx_packets = stats.opackets;
    if (rx_bytes) *rx_bytes = stats.ibytes;
    if (tx_bytes) *tx_bytes = stats.obytes;

    return 0;
}

void dpdk_cleanup(void)
{
    printf("Cleaning up DPDK resources...\n");
    
    /* Stop the port */
    if (rte_eth_dev_is_valid_port(g_port_id)) {
        rte_eth_dev_stop(g_port_id);
        rte_eth_dev_close(g_port_id);
    }

    /* Cleanup EAL */
    rte_eal_cleanup();
    
    printf("DPDK cleanup completed\n");
}
