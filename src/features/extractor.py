"""
Network flow feature extractor for packet analysis.
Extracts comprehensive flow features from captured packets.
"""

import struct
import time
import hashlib
import logging
from collections import defaultdict

class FeatureExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.flows = defaultdict(dict)
        self.flow_timeout = 600  # 10 minutes
        
    def parse_ethernet_header(self, data):
        """Parse Ethernet header from packet data."""
        if len(data) < 14:
            return None
            
        # Ethernet header: dst_mac(6) + src_mac(6) + ethertype(2)
        eth_header = struct.unpack('!6s6sH', data[:14])
        return {
            'dst_mac': eth_header[0],
            'src_mac': eth_header[1],
            'ethertype': eth_header[2],
            'payload': data[14:]
        }
    
    def parse_ip_header(self, data):
        """Parse IP header from packet data."""
        if len(data) < 20:
            return None
            
        # IP header (minimum 20 bytes)
        ip_header = struct.unpack('!BBHHHBBH4s4s', data[:20])
        
        version = (ip_header[0] >> 4) & 0xF
        ihl = ip_header[0] & 0xF
        header_length = ihl * 4
        
        if version != 4 or len(data) < header_length:
            return None
            
        return {
            'version': version,
            'ihl': ihl,
            'tos': ip_header[1],
            'total_length': ip_header[2],
            'identification': ip_header[3],
            'flags': ip_header[4] >> 13,
            'fragment_offset': ip_header[4] & 0x1FFF,
            'ttl': ip_header[5],
            'protocol': ip_header[6],
            'checksum': ip_header[7],
            'src_ip': ip_header[8],
            'dst_ip': ip_header[9],
            'header_length': header_length,
            'payload': data[header_length:]
        }
    
    def parse_tcp_header(self, data):
        """Parse TCP header from packet data."""
        if len(data) < 20:
            return None
            
        # TCP header (minimum 20 bytes)
        tcp_header = struct.unpack('!HHLLBBHHH', data[:20])
        
        data_offset = (tcp_header[4] >> 4) & 0xF
        header_length = data_offset * 4
        
        if len(data) < header_length:
            return None
            
        return {
            'src_port': tcp_header[0],
            'dst_port': tcp_header[1],
            'seq_num': tcp_header[2],
            'ack_num': tcp_header[3],
            'data_offset': data_offset,
            'flags': tcp_header[5],
            'window': tcp_header[6],
            'checksum': tcp_header[7],
            'urgent_ptr': tcp_header[8],
            'header_length': header_length,
            'payload': data[header_length:]
        }
    
    def parse_udp_header(self, data):
        """Parse UDP header from packet data."""
        if len(data) < 8:
            return None
            
        # UDP header (8 bytes)
        udp_header = struct.unpack('!HHHH', data[:8])
        
        return {
            'src_port': udp_header[0],
            'dst_port': udp_header[1],
            'length': udp_header[2],
            'checksum': udp_header[3],
            'payload': data[8:]
        }
    
    def get_flow_key(self, src_ip, dst_ip, src_port, dst_port, protocol):
        """Generate a unique flow key."""
        # Normalize flow direction (smaller IP first)
        if src_ip < dst_ip or (src_ip == dst_ip and src_port < dst_port):
            key = f"{src_ip}:{src_port}-{dst_ip}:{dst_port}:{protocol}"
        else:
            key = f"{dst_ip}:{dst_port}-{src_ip}:{src_port}:{protocol}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def update_flow_stats(self, flow_key, packet_info):
        """Update flow statistics with new packet."""
        flow = self.flows[flow_key]
        current_time = time.time()
        
        # Initialize flow if new
        if 'start_time' not in flow:
            flow['start_time'] = current_time
            flow['src_ip'] = packet_info['src_ip']
            flow['dst_ip'] = packet_info['dst_ip']
            flow['src_port'] = packet_info.get('src_port', 0)
            flow['dst_port'] = packet_info.get('dst_port', 0)
            flow['protocol'] = packet_info['protocol']
            flow['packet_count'] = 0
            flow['byte_count'] = 0
            flow['tcp_flags'] = 0
            flow['packet_lengths'] = []
            flow['inter_arrival_times'] = []
            flow['last_packet_time'] = current_time
            
        # Update statistics
        flow['packet_count'] += 1
        flow['byte_count'] += packet_info['packet_length']
        flow['packet_lengths'].append(packet_info['packet_length'])
        
        # Calculate inter-arrival time
        if flow['packet_count'] > 1:
            inter_arrival = current_time - flow['last_packet_time']
            flow['inter_arrival_times'].append(inter_arrival)
            
        flow['last_packet_time'] = current_time
        
        # Update TCP flags if TCP packet
        if packet_info['protocol'] == 6 and 'tcp_flags' in packet_info:
            flow['tcp_flags'] |= packet_info['tcp_flags']
    
    def calculate_flow_features(self, flow):
        """Calculate comprehensive flow features."""
        if not flow or flow['packet_count'] == 0:
            return None
            
        features = {}
        
        # Basic flow information
        features['src_ip'] = self.ip_to_string(flow['src_ip'])
        features['dst_ip'] = self.ip_to_string(flow['dst_ip'])
        features['src_port'] = flow['src_port']
        features['dst_port'] = flow['dst_port']
        features['protocol'] = flow['protocol']
        
        # Timing features
        flow_duration = flow['last_packet_time'] - flow['start_time']
        features['flow_duration'] = max(flow_duration, 0.000001)  # Avoid division by zero
        
        # Packet and byte statistics
        features['total_fwd_packets'] = flow['packet_count']
        features['total_bwd_packets'] = 0  # Simplified - would need bidirectional analysis
        features['total_length_fwd_packets'] = flow['byte_count']
        features['total_length_bwd_packets'] = 0
        
        # Packet length statistics
        lengths = flow['packet_lengths']
        if lengths:
            features['packet_length_max'] = max(lengths)
            features['packet_length_min'] = min(lengths)
            features['packet_length_mean'] = sum(lengths) / len(lengths)
            features['packet_length_std'] = self.calculate_std(lengths)
        else:
            features['packet_length_max'] = 0
            features['packet_length_min'] = 0
            features['packet_length_mean'] = 0
            features['packet_length_std'] = 0
            
        # Flow rate features
        features['flow_bytes_per_second'] = flow['byte_count'] / features['flow_duration']
        features['flow_packets_per_second'] = flow['packet_count'] / features['flow_duration']
        
        # Inter-arrival time statistics
        if flow['inter_arrival_times']:
            iat = flow['inter_arrival_times']
            features['flow_iat_mean'] = sum(iat) / len(iat)
            features['flow_iat_std'] = self.calculate_std(iat)
            features['flow_iat_max'] = max(iat)
            features['flow_iat_min'] = min(iat)
        else:
            features['flow_iat_mean'] = 0
            features['flow_iat_std'] = 0
            features['flow_iat_max'] = 0
            features['flow_iat_min'] = 0
            
        # TCP-specific features
        if flow['protocol'] == 6:
            features['tcp_flags'] = flow.get('tcp_flags', 0)
            features['fin_flag_count'] = 1 if (flow['tcp_flags'] & 0x01) else 0
            features['syn_flag_count'] = 1 if (flow['tcp_flags'] & 0x02) else 0
            features['rst_flag_count'] = 1 if (flow['tcp_flags'] & 0x04) else 0
            features['psh_flag_count'] = 1 if (flow['tcp_flags'] & 0x08) else 0
            features['ack_flag_count'] = 1 if (flow['tcp_flags'] & 0x10) else 0
            features['urg_flag_count'] = 1 if (flow['tcp_flags'] & 0x20) else 0
        else:
            features['tcp_flags'] = 0
            features['fin_flag_count'] = 0
            features['syn_flag_count'] = 0
            features['rst_flag_count'] = 0
            features['psh_flag_count'] = 0
            features['ack_flag_count'] = 0
            features['urg_flag_count'] = 0
            
        # Additional derived features
        features['avg_packet_size'] = features['packet_length_mean']
        features['packet_length_variance'] = features['packet_length_std'] ** 2
        
        # Timestamp
        features['timestamp'] = int(time.time() * 1000000)  # Microseconds
        
        # Label (simplified - in real scenarios this would come from ML model or rules)
        features['label'] = 'BENIGN'
        
        return features
    
    def ip_to_string(self, ip_bytes):
        """Convert IP bytes to string format."""
        if isinstance(ip_bytes, bytes) and len(ip_bytes) == 4:
            return '.'.join(str(b) for b in ip_bytes)
        return str(ip_bytes)
    
    def calculate_std(self, values):
        """Calculate standard deviation of a list of values."""
        if len(values) < 2:
            return 0
            
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def cleanup_old_flows(self):
        """Remove old flows to prevent memory leaks."""
        current_time = time.time()
        expired_flows = []
        
        for flow_key, flow in self.flows.items():
            if current_time - flow['last_packet_time'] > self.flow_timeout:
                expired_flows.append(flow_key)
                
        for flow_key in expired_flows:
            del self.flows[flow_key]
            
        if expired_flows:
            self.logger.debug(f"Cleaned up {len(expired_flows)} expired flows")
    
    def extract_features(self, packet):
        """Main function to extract features from a packet."""
        try:
            # Clean up old flows periodically
            if len(self.flows) > 1000:
                self.cleanup_old_flows()
                
            packet_data = packet['data']
            packet_length = packet['length']
            
            # Parse Ethernet header
            eth = self.parse_ethernet_header(packet_data)
            if not eth or eth['ethertype'] != 0x0800:  # Only IPv4
                return None
                
            # Parse IP header
            ip = self.parse_ip_header(eth['payload'])
            if not ip:
                return None
                
            packet_info = {
                'src_ip': ip['src_ip'],
                'dst_ip': ip['dst_ip'],
                'protocol': ip['protocol'],
                'packet_length': packet_length
            }
            
            # Parse transport layer
            if ip['protocol'] == 6:  # TCP
                tcp = self.parse_tcp_header(ip['payload'])
                if tcp:
                    packet_info['src_port'] = tcp['src_port']
                    packet_info['dst_port'] = tcp['dst_port']
                    packet_info['tcp_flags'] = tcp['flags']
            elif ip['protocol'] == 17:  # UDP
                udp = self.parse_udp_header(ip['payload'])
                if udp:
                    packet_info['src_port'] = udp['src_port']
                    packet_info['dst_port'] = udp['dst_port']
            else:
                # Other protocols
                packet_info['src_port'] = 0
                packet_info['dst_port'] = 0
                
            # Generate flow key and update statistics
            flow_key = self.get_flow_key(
                packet_info['src_ip'],
                packet_info['dst_ip'],
                packet_info.get('src_port', 0),
                packet_info.get('dst_port', 0),
                packet_info['protocol']
            )
            
            self.update_flow_stats(flow_key, packet_info)
            
            # Extract features for this flow
            features = self.calculate_flow_features(self.flows[flow_key])
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error extracting features: {e}")
            return None
