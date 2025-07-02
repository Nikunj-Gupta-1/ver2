"""
Kafka producer for streaming network flow features.
Handles real-time data streaming to Apache Kafka.
"""

import json
import logging
import time
from confluent_kafka import Producer, KafkaException

class KafkaProducer:
    def __init__(self, config_file='config/kafka.properties'):
        self.logger = logging.getLogger(__name__)
        self.producer = None
        self.topic = 'network-flows'
        self.config_file = config_file
        self.message_count = 0
        
    def load_config(self):
        """Load Kafka configuration from file."""
        config = {
            'bootstrap.servers': 'localhost:9092',
            'client.id': 'dpdk-network-capture',
            'batch.size': 16384,
            'linger.ms': 10,
            'compression.type': 'snappy',
            'acks': 1,
            'retries': 3,
            'retry.backoff.ms': 100
        }
        
        try:
            with open(self.config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        except FileNotFoundError:
            self.logger.warning(f"Config file {self.config_file} not found, using defaults")
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            
        return config
        
    def initialize(self):
        """Initialize Kafka producer."""
        try:
            config = self.load_config()
            self.producer = Producer(config)
            
            # Test connection by getting metadata
            metadata = self.producer.list_topics(timeout=5)
            self.logger.info(f"Connected to Kafka cluster with {len(metadata.brokers)} brokers")
            
            return True
            
        except KafkaException as e:
            self.logger.error(f"Kafka connection failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to initialize Kafka producer: {e}")
            return False
            
    def delivery_callback(self, err, msg):
        """Callback for message delivery confirmation."""
        if err:
            self.logger.error(f"Message delivery failed: {err}")
        else:
            self.message_count += 1
            if self.message_count % 1000 == 0:
                self.logger.info(f"Delivered {self.message_count} messages to Kafka")
                
    def send_features(self, features):
        """Send network flow features to Kafka."""
        if not self.producer:
            self.logger.error("Kafka producer not initialized")
            return False
            
        try:
            # Convert features to JSON
            message = json.dumps(features, default=str)
            
            # Create message key from flow information
            key = f"{features.get('src_ip', '')}:{features.get('src_port', '')}-{features.get('dst_ip', '')}:{features.get('dst_port', '')}"
            
            # Send message
            self.producer.produce(
                topic=self.topic,
                key=key,
                value=message,
                callback=self.delivery_callback
            )
            
            # Trigger delivery callbacks
            self.producer.poll(0)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending message to Kafka: {e}")
            return False
            
    def send_batch(self, features_list):
        """Send a batch of features to Kafka."""
        if not self.producer:
            self.logger.error("Kafka producer not initialized")
            return 0
            
        sent_count = 0
        for features in features_list:
            if self.send_features(features):
                sent_count += 1
                
        # Flush to ensure delivery
        self.producer.flush(timeout=1.0)
        
        return sent_count
        
    def get_statistics(self):
        """Get producer statistics."""
        if not self.producer:
            return {}
            
        try:
            stats = json.loads(self.producer.stats())
            return {
                'messages_sent': self.message_count,
                'txmsgs': stats.get('txmsgs', 0),
                'txmsg_bytes': stats.get('txmsg_bytes', 0),
                'brokers': len(stats.get('brokers', {}))
            }
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {'messages_sent': self.message_count}
            
    def cleanup(self):
        """Cleanup Kafka producer resources."""
        if self.producer:
            try:
                # Wait for any pending messages to be delivered
                self.producer.flush(timeout=10.0)
                self.logger.info(f"Kafka producer cleaned up. Total messages sent: {self.message_count}")
            except Exception as e:
                self.logger.error(f"Error during Kafka cleanup: {e}")
            finally:
                self.producer = None
