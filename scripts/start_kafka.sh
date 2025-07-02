#!/bin/bash
# Start Kafka services

KAFKA_HOME="/opt/kafka"
CONFIG_DIR="$(pwd)/config"

# Check if Kafka is installed
if [ ! -d "$KAFKA_HOME" ]; then
    echo "Error: Kafka not found at $KAFKA_HOME"
    echo "Please install Kafka first"
    exit 1
fi

# Check if config files exist
if [ ! -f "$CONFIG_DIR/server.properties" ]; then
    echo "Error: server.properties not found in $CONFIG_DIR"
    exit 1
fi

# Function to check if a service is running
check_service() {
    local service_name="$1"
    local port="$2"
    
    if netcat -z localhost "$port" 2>/dev/null; then
        echo "$service_name is already running on port $port"
        return 0
    else
        return 1
    fi
}

# Start ZooKeeper
start_zookeeper() {
    if check_service "ZooKeeper" 2181; then
        return 0
    fi
    
    echo "Starting ZooKeeper..."
    cd "$KAFKA_HOME"
    
    # Start ZooKeeper in background
    nohup bin/zookeeper-server-start.sh config/zookeeper.properties > logs/zookeeper.log 2>&1 &
    ZOOKEEPER_PID=$!
    
    # Wait for ZooKeeper to start
    echo "Waiting for ZooKeeper to start..."
    for i in {1..30}; do
        if check_service "ZooKeeper" 2181; then
            echo "ZooKeeper started successfully (PID: $ZOOKEEPER_PID)"
            return 0
        fi
        sleep 1
    done
    
    echo "Error: ZooKeeper failed to start"
    return 1
}

# Start Kafka
start_kafka() {
    if check_service "Kafka" 9092; then
        return 0
    fi
    
    echo "Starting Kafka..."
    cd "$KAFKA_HOME"
    
    # Use custom config if available
    local config_file="config/server.properties"
    if [ -f "$CONFIG_DIR/server.properties" ]; then
        config_file="$CONFIG_DIR/server.properties"
        echo "Using custom configuration: $config_file"
    fi
    
    # Start Kafka in background
    nohup bin/kafka-server-start.sh "$config_file" > logs/kafka.log 2>&1 &
    KAFKA_PID=$!
    
    # Wait for Kafka to start
    echo "Waiting for Kafka to start..."
    for i in {1..60}; do
        if check_service "Kafka" 9092; then
            echo "Kafka started successfully (PID: $KAFKA_PID)"
            return 0
        fi
        sleep 1
    done
    
    echo "Error: Kafka failed to start"
    return 1
}

# Create topic if needed
create_topic() {
    local topic_name="network-flows"
    
    echo "Creating topic: $topic_name"
    cd "$KAFKA_HOME"
    
    # Check if topic exists
    if bin/kafka-topics.sh --bootstrap-server localhost:9092 --list | grep -q "$topic_name"; then
        echo "Topic $topic_name already exists"
        return 0
    fi
    
    # Create topic
    bin/kafka-topics.sh --create \
        --bootstrap-server localhost:9092 \
        --topic "$topic_name" \
        --partitions 3 \
        --replication-factor 1
        
    if [ $? -eq 0 ]; then
        echo "Topic $topic_name created successfully"
    else
        echo "Warning: Failed to create topic $topic_name"
    fi
}

# Main execution
echo "Starting Kafka services..."

# Create logs directory if it doesn't exist
mkdir -p "$KAFKA_HOME/logs"

# Start services
if start_zookeeper && start_kafka; then
    echo "Services started successfully!"
    
    # Wait a bit for services to fully initialize
    sleep 5
    
    # Create topic
    create_topic
    
    echo ""
    echo "Kafka services are running:"
    echo "  ZooKeeper: localhost:2181"
    echo "  Kafka: localhost:9092"
    echo ""
    echo "To stop services, run: ./scripts/stop_kafka.sh"
    echo "To view logs: tail -f $KAFKA_HOME/logs/kafka.log"
    
else
    echo "Failed to start services"
    exit 1
fi
