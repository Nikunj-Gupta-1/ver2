#!/bin/bash
# Network interface binding script for DPDK

DPDK_DEVBIND="/opt/dpdk/usertools/dpdk-devbind.py"

# Check if dpdk-devbind exists, try alternative locations
if [ ! -f "$DPDK_DEVBIND" ]; then
    DPDK_DEVBIND="/usr/share/dpdk/usertools/dpdk-devbind.py"
fi

if [ ! -f "$DPDK_DEVBIND" ]; then
    # Use system dpdk-devbind if available
    if command -v dpdk-devbind.py &> /dev/null; then
        DPDK_DEVBIND="dpdk-devbind.py"
    else
        echo "Error: dpdk-devbind.py not found"
        echo "Please install DPDK or set correct path"
        exit 1
    fi
fi

show_usage() {
    echo "Usage: $0 <command> [options]"
    echo "Commands:"
    echo "  list                 - List all network interfaces"
    echo "  status              - Show interface binding status"
    echo "  bind <pci> <driver> - Bind interface to driver"
    echo "  unbind <pci>        - Unbind interface from driver"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 status"
    echo "  $0 bind 0000:02:00.0 vfio-pci"
    echo "  $0 unbind 0000:02:00.0"
}

list_interfaces() {
    echo "Network interfaces:"
    ip link show | grep -E '^[0-9]+:' | cut -d: -f2 | sed 's/^ *//'
    echo ""
    echo "PCI devices:"
    lspci | grep -i ethernet
}

show_status() {
    echo "DPDK Interface Status:"
    python3 "$DPDK_DEVBIND" --status-dev net
}

bind_interface() {
    local pci="$1"
    local driver="$2"
    
    if [ -z "$pci" ] || [ -z "$driver" ]; then
        echo "Error: PCI address and driver required"
        echo "Usage: $0 bind <pci_address> <driver>"
        return 1
    fi
    
    echo "Binding interface $pci to driver $driver..."
    
    # Load driver module if needed
    if [ "$driver" = "vfio-pci" ]; then
        echo "Loading vfio-pci module..."
        sudo modprobe vfio-pci
    elif [ "$driver" = "uio_pci_generic" ]; then
        echo "Loading uio_pci_generic module..."
        sudo modprobe uio_pci_generic
    fi
    
    # Bind the device
    sudo python3 "$DPDK_DEVBIND" --bind="$driver" "$pci"
    
    if [ $? -eq 0 ]; then
        echo "Successfully bound $pci to $driver"
    else
        echo "Failed to bind interface"
        return 1
    fi
}

unbind_interface() {
    local pci="$1"
    
    if [ -z "$pci" ]; then
        echo "Error: PCI address required"
        echo "Usage: $0 unbind <pci_address>"
        return 1
    fi
    
    echo "Unbinding interface $pci..."
    sudo python3 "$DPDK_DEVBIND" --unbind "$pci"
    
    if [ $? -eq 0 ]; then
        echo "Successfully unbound $pci"
    else
        echo "Failed to unbind interface"
        return 1
    fi
}

# Main script logic
case "$1" in
    "list")
        list_interfaces
        ;;
    "status")
        show_status
        ;;
    "bind")
        bind_interface "$2" "$3"
        ;;
    "unbind")
        unbind_interface "$2"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
