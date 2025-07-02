#!/bin/bash
# Stop Kafka services

KAFKA_HOME="/opt/kafka"

# Check if Kafka is installed
if [ ! -d "$KAFKA_HOME" ]; then
    echo "Error: Kafka not found at $KAFKA_HOME"
    exit 1
fi

# Parse command line arguments
CLEAN_LOGS=false
if [ "$1" = "--clean-logs" ]; then
    CLEAN_LOGS=true
fi

# Function to stop a process by name
stop_process() {
    local process_name="$1"
    local pids=$(jps | grep "$process_name" | cut -d' ' -f1)
    
    if [ -z "$pids" ]; then
        echo "$process_name is not running"
        return 0
    fi
    
    echo "Stopping $process_name (PIDs: $pids)..."
    for pid in $pids; do
        kill "$pid"
    done
    
    # Wait for processes to stop
    sleep 5
    
    # Check if processes are still running
    remaining_pids=$(jps | grep "$process_name" | cut -d' ' -f1)
    if [ -n "$remaining_pids" ]; then
        echo "Force killing $process_name (PIDs: $remaining_pids)..."
        for pid in $remaining_pids; do
            kill -9 "$pid"
        done
    fi
    
    echo "$process_name stopped"
}

# Stop Kafka
echo "Stopping Kafka services..."

cd "$KAFKA_HOME"

# Stop Kafka server
stop_process "Kafka"

# Stop ZooKeeper
stop_process "QuorumPeerMain"

# Clean logs if requested
if [ "$CLEAN_LOGS" = true ]; then
    echo "Cleaning Kafka logs..."
    rm -rf logs/*
    echo "Logs cleaned"
fi

echo "Kafka services stopped"

# Verify services are stopped
echo "Verifying services are stopped..."
sleep 2

if jps | grep -E "(Kafka|QuorumPeerMain)" > /dev/null; then
    echo "Warning: Some Kafka processes may still be running:"
    jps | grep -E "(Kafka|QuorumPeerMain)"
else
    echo "All Kafka services stopped successfully"
fi
