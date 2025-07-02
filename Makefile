# Makefile for DPDK packet capture library

CC = gcc
CFLAGS = -O3 -Wall -Wextra -fPIC
LDFLAGS = -shared
INCLUDES = $(shell pkg-config --cflags libdpdk)
LIBS = $(shell pkg-config --libs libdpdk) -lnuma -lpcap

TARGET = libdpdk_capture.so
SOURCES = src/dpdk/libdpdk_capture.c
HEADERS = src/dpdk/dpdk_capture.h

.PHONY: all clean install uninstall

all: $(TARGET)

$(TARGET): $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) $(INCLUDES) $(LDFLAGS) -o $@ $(SOURCES) $(LIBS)

clean:
	rm -f $(TARGET)

install: $(TARGET)
	sudo cp $(TARGET) /usr/local/lib/
	sudo ldconfig

uninstall:
	sudo rm -f /usr/local/lib/$(TARGET)
	sudo ldconfig

check:
	@echo "Checking DPDK installation..."
	@pkg-config --exists libdpdk && echo "DPDK found" || echo "DPDK not found"
	@echo "Checking required libraries..."
	@pkg-config --exists libnuma && echo "libnuma found" || echo "libnuma not found"
	@echo "Build flags:"
	@echo "INCLUDES: $(INCLUDES)"
	@echo "LIBS: $(LIBS)"
