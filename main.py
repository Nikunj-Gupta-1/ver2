#!/usr/bin/env python3
"""
Main application for DPDK network packet capture and analysis.
Coordinates DPDK packet capture, feature extraction, and Kafka streaming.
"""

import argparse
import sys
import time
import signal
import logging
from src.dpdk.packet_capture import DPDKPacketCapture
from src.features.extractor import FeatureExtractor
from src.kafka.producer import KafkaProducer

class NetworkCaptureApp:
    def __init__(self, port=0, cores="0", batch_size=32, kafka_enabled=True, verbose=False):
        self.port = port
        self.cores = cores
        self.batch_size = batch_size
        self.kafka_enabled = kafka_enabled
        self.verbose = verbose
        self.running = True
        
        # Initialize components
        self.packet_capture = None
        self.feature_extractor = FeatureExtractor()
        self.kafka_producer = KafkaProducer() if kafka_enabled else None
        
        # Setup logging
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info("Received shutdown signal, stopping application...")
        self.running = False
        
    def initialize(self):
        """Initialize all components."""
        try:
            # Setup signal handlers
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # Initialize DPDK
            self.logger.info("Initializing DPDK packet capture...")
            self.packet_capture = DPDKPacketCapture(
                port=self.port,
                cores=self.cores,
                batch_size=self.batch_size
            )
            
            if not self.packet_capture.initialize():
                raise RuntimeError("Failed to initialize DPDK")
                
            # Initialize Kafka if enabled
            if self.kafka_enabled:
                self.logger.info("Initializing Kafka producer...")
                if not self.kafka_producer.initialize():
                    raise RuntimeError("Failed to initialize Kafka producer")
                    
            self.logger.info("Application initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False
            
    def process_packets(self, packets):
        """Process captured packets and extract features."""
        if not packets:
            return
            
        processed_count = 0
        for packet in packets:
            try:
                # Extract features from packet
                features = self.feature_extractor.extract_features(packet)
                
                if features:
                    # Send to Kafka if enabled
                    if self.kafka_enabled and self.kafka_producer:
                        self.kafka_producer.send_features(features)
                    
                    # Print features if verbose mode
                    if self.verbose:
                        self.logger.debug(f"Features: {features}")
                        
                    processed_count += 1
                    
            except Exception as e:
                self.logger.error(f"Error processing packet: {e}")
                
        if processed_count > 0:
            self.logger.info(f"Processed {processed_count} packets")
            
    def run(self):
        """Main application loop."""
        if not self.initialize():
            return 1
            
        self.logger.info("Starting packet capture loop...")
        packets_captured = 0
        
        try:
            while self.running:
                # Capture packets
                packets = self.packet_capture.capture_packets()
                
                if packets:
                    packets_captured += len(packets)
                    self.process_packets(packets)
                    
                    if self.verbose:
                        self.logger.debug(f"Total packets captured: {packets_captured}")
                else:
                    # Short sleep to prevent CPU spinning
                    time.sleep(0.001)
                    
        except Exception as e:
            self.logger.error(f"Runtime error: {e}")
            return 1
            
        finally:
            self.cleanup()
            
        self.logger.info(f"Application stopped. Total packets captured: {packets_captured}")
        return 0
        
    def cleanup(self):
        """Cleanup resources."""
        try:
            if self.packet_capture:
                self.packet_capture.cleanup()
                
            if self.kafka_producer:
                self.kafka_producer.cleanup()
                
            self.logger.info("Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")

def main():
    parser = argparse.ArgumentParser(description='DPDK Network Packet Capture Application')
    parser.add_argument('--port', type=int, default=0, help='DPDK port number (default: 0)')
    parser.add_argument('--cores', type=str, default='0', help='CPU cores for DPDK (default: 0)')
    parser.add_argument('--batch-size', type=int, default=32, help='Packet batch size (default: 32)')
    parser.add_argument('--no-kafka', action='store_true', help='Disable Kafka output')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Check if running as root (required for DPDK)
    if os.geteuid() != 0:
        print("Error: This application requires root privileges for DPDK operations.")
        print("Please run with sudo: sudo python3 main.py")
        return 1
    
    app = NetworkCaptureApp(
        port=args.port,
        cores=args.cores,
        batch_size=args.batch_size,
        kafka_enabled=not args.no_kafka,
        verbose=args.verbose
    )
    
    return app.run()

if __name__ == "__main__":
    import os
    sys.exit(main())
