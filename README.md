# DPDK Network Capture Application

A high-performance network packet capture application using DPDK (Data Plane Development Kit) for kernel-bypass packet processing and Apache Kafka for real-time data streaming.

## Features

- High-performance packet capture using DPDK
- Real-time network flow feature extraction
- Kafka integration for data streaming
- Comprehensive network flow analysis (50+ features)
- Simple command-line interface
- Detailed logging and monitoring

## System Requirements

- Ubuntu 20.04+ or Debian 11+
- Intel processor with SSE4.2 support
- At least 4GB RAM (8GB recommended)
- DPDK-compatible network interface
- Root/sudo access for DPDK operations

## Quick Start

1. Clone and setup the project:
```bash
git clone <repository-url>
cd dpdk-network-capture
```

2. Install dependencies:
```bash
sudo apt update
sudo apt install -y build-essential cmake git wget curl
sudo apt install -y pkg-config libnuma-dev libpcap-dev
sudo apt install -y linux-headers-$(uname -r)
sudo apt install -y python3 python3-pip python3-dev
sudo apt install -y openjdk-11-jdk netcat-openbsd
sudo apt install -y dpdk dpdk-dev
```

3. Install Python packages:
```bash
pip3 install -r requirements.txt
```

4. Build the DPDK library:
```bash
make
```

5. Configure the system:
```bash
# Configure hugepages
echo 1024 | sudo tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
sudo mkdir -p /mnt/huge
sudo mount -t hugetlbfs nodev /mnt/huge

# Load DPDK drivers
sudo modprobe uio
sudo modprobe vfio-pci
```

6. Install and start Kafka:
```bash
cd /tmp
wget https://downloads.apache.org/kafka/3.8.1/kafka_2.13-3.8.1.tgz
tar -xzf kafka_2.13-3.8.1.tgz
sudo mv kafka_2.13-3.8.1 /opt/kafka
sudo useradd -m -s /bin/bash kafka
sudo chown -R kafka:kafka /opt/kafka

# Start Kafka services
./scripts/start_kafka.sh
```

7. Bind network interface:
```bash
# Check available interfaces
./scripts/bind_interface.sh list

# Bind interface to DPDK
sudo ./scripts/bind_interface.sh bind 0000:XX:XX.X vfio-pci
```

8. Test the system:
```bash
python3 test_system.py
```

9. Run the application:
```bash
sudo python3 main.py
```

## Usage

### Basic Usage
```bash
sudo python3 main.py
```

### Advanced Options
```bash
# Specify DPDK port and CPU cores
sudo python3 main.py --port 0 --cores 0-1

# Adjust batch size for performance
sudo python3 main.py --batch-size 64

# Run without Kafka (for testing)
sudo python3 main.py --no-kafka

# Enable verbose logging
sudo python3 main.py --verbose
```

## Configuration

### Kafka Configuration
Edit `config/kafka.properties` to customize Kafka producer settings:
- Batch size and linger time for throughput optimization
- Compression settings
- Topic configuration

### DPDK Configuration
The application automatically configures DPDK based on command-line arguments:
- Port selection
- CPU core assignment
- Memory pool sizing
- Packet batch processing

## Project Structure

```
dpdk-network-capture/
├── main.py                    # Main application entry point
├── requirements.txt           # Python dependencies
├── Makefile                  # Build system
├── test_system.py            # System verification
├── README.md                 # This file
├── src/
│   ├── dpdk/                 # DPDK integration
│   ├── features/             # Feature extraction
│   └── kafka/                # Kafka producer
├── config/                   # Configuration files
└── scripts/                  # Management scripts
```

## Output Data Format

The application produces JSON messages with network flow features:

```json
{
  "src_ip": "192.168.1.100",
  "dst_ip": "192.168.1.1", 
  "src_port": 12345,
  "dst_port": 80,
  "protocol": 6,
  "packet_length": 1514,
  "tcp_flags": 24,
  "flow_duration": 1.5,
  "total_fwd_packets": 10,
  "packet_length_mean": 892.3,
  "flow_bytes_per_second": 15420.7,
  "timestamp": 1672531200000000,
  "label": "BENIGN"
}
```

## Troubleshooting

### Common Issues

1. **Permission denied**: Ensure running as root with `sudo`
2. **No Ethernet ports**: Check network interface binding with `./scripts/bind_interface.sh status`
3. **IOMMU not found**: Enable IOMMU in GRUB configuration
4. **Hugepages allocation failed**: Check hugepage configuration
5. **Kafka connection errors**: Verify Kafka services are running

### Debug Commands

```bash
# Check system status
python3 test_system.py

# Check interface binding
./scripts/bind_interface.sh status

# Check Kafka services
jps | grep -E "(Kafka|QuorumPeerMain)"

# Check hugepages
cat /proc/meminfo | grep Huge

# Check DPDK installation
pkg-config --exists libdpdk && echo "DPDK OK"
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Run `python3 test_system.py` to diagnose issues
3. Check logs for detailed error messages
4. Open an issue on GitHub
