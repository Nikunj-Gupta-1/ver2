
"""
System configuration verification for DPDK network capture application.
Tests all dependencies and system settings.
"""

import os
import sys
import subprocess
import json
import logging

class SystemTester:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.results = {}
        
    def run_command(self, cmd, check=True):
        """Run shell command and return output."""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
            return result.stdout.strip(), result.returncode
        except subprocess.CalledProcessError as e:
            return e.stdout.strip() if e.stdout else "", e.returncode
            
    def test_python_dependencies(self):
        """Test Python package dependencies."""
        self.logger.info("Testing Python dependencies...")
        
        required_packages = {
            'confluent_kafka': 'confluent-kafka',
            'ctypes': 'built-in',
            'numpy': 'numpy',
            'psutil': 'psutil'
        }
        
        missing = []
        for package, pip_name in required_packages.items():
            try:
                __import__(package)
                self.logger.info(f"✓ {package} is available")
            except ImportError:
                self.logger.error(f"✗ {package} is missing (install with: pip3 install {pip_name})")
                missing.append(pip_name)
                
        self.results['python_dependencies'] = {
            'status': 'PASS' if not missing else 'FAIL',
            'missing_packages': missing
        }
        
    def test_dpdk_installation(self):
        """Test DPDK installation and configuration."""
        self.logger.info("Testing DPDK installation...")
        
        # Check DPDK library
        output, code = self.run_command("pkg-config --exists libdpdk", check=False)
        if code == 0:
            self.logger.info("✓ DPDK library found")
            
            # Get DPDK version
            version, _ = self.run_command("pkg-config --modversion libdpdk")
            self.logger.info(f"✓ DPDK version: {version}")
            
            self.results['dpdk'] = {'status': 'PASS', 'version': version}
        else:
            self.logger.error("✗ DPDK library not found")
            self.results['dpdk'] = {'status': 'FAIL', 'error': 'Library not found'}
            
    def test_hugepages(self):
        """Test hugepages configuration."""
        self.logger.info("Testing hugepages configuration...")
        
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                
            hugepages_total = 0
            hugepages_free = 0
            
            for line in meminfo.split('\n'):
                if line.startswith('HugePages_Total:'):
                    hugepages_total = int(line.split()[1])
                elif line.startswith('HugePages_Free:'):
                    hugepages_free = int(line.split()[1])
                    
            if hugepages_total > 0:
                self.logger.info(f"✓ Hugepages configured: {hugepages_total} total, {hugepages_free} free")
                self.results['hugepages'] = {
                    'status': 'PASS',
                    'total': hugepages_total,
                    'free': hugepages_free
                }
            else:
                self.logger.error("✗ No hugepages configured")
                self.results['hugepages'] = {'status': 'FAIL', 'error': 'No hugepages configured'}
                
        except Exception as e:
            self.logger.error(f"✗ Failed to check hugepages: {e}")
            self.results['hugepages'] = {'status': 'FAIL', 'error': str(e)}
            
    def test_vfio_driver(self):
        """Test VFIO driver loading."""
        self.logger.info("Testing VFIO driver...")
        
        output, code = self.run_command("lsmod | grep vfio", check=False)
        if code == 0 and 'vfio' in output:
            self.logger.info("✓ VFIO driver loaded")
            self.results['vfio'] = {'status': 'PASS'}
        else:
            self.logger.error("✗ VFIO driver not loaded")
            self.results['vfio'] = {'status': 'FAIL', 'error': 'Driver not loaded'}
            
    def test_kafka_installation(self):
        """Test Kafka installation."""
        self.logger.info("Testing Kafka installation...")
        
        kafka_paths = ['/opt/kafka', '/usr/local/kafka']
        kafka_found = False
        
        for path in kafka_paths:
            if os.path.exists(path):
                self.logger.info(f"✓ Kafka found at {path}")
                kafka_found = True
                self.results['kafka'] = {'status': 'PASS', 'path': path}
                break
                
        if not kafka_found:
            self.logger.error("✗ Kafka not found")
            self.results['kafka'] = {'status': 'FAIL', 'error': 'Kafka not found'}
            
    def test_kafka_services(self):
        """Test Kafka service availability."""
        self.logger.info("Testing Kafka services...")
        
        # Check if Kafka processes are running
        output, code = self.run_command("jps | grep -E '(Kafka|QuorumPeerMain)'", check=False)
        
        if code == 0 and output:
            services = output.split('\n')
            self.logger.info(f"✓ Kafka services running: {len(services)} processes")
            self.results['kafka_services'] = {'status': 'PASS', 'processes': services}
        else:
            self.logger.warning("⚠ Kafka services not running (this is okay if not started yet)")
            self.results['kafka_services'] = {'status': 'WARNING', 'error': 'Services not running'}
            
    def test_network_interfaces(self):
        """Test network interface availability."""
        self.logger.info("Testing network interfaces...")
        
        # Get list of network interfaces
        output, code = self.run_command("ip link show", check=False)
        
        if code == 0:
            interfaces = []
            for line in output.split('\n'):
                if ': ' in line and not line.startswith(' '):
                    interface = line.split(':')[1].strip().split('@')[0]
                    if interface != 'lo':  # Skip loopback
                        interfaces.append(interface)
                        
            self.logger.info(f"✓ Network interfaces found: {', '.join(interfaces)}")
            self.results['network_interfaces'] = {'status': 'PASS', 'interfaces': interfaces}
        else:
            self.logger.error("✗ Failed to get network interfaces")
            self.results['network_interfaces'] = {'status': 'FAIL', 'error': 'Failed to list interfaces'}
            
    def test_library_compilation(self):
        """Test DPDK library compilation."""
        self.logger.info("Testing library compilation...")
        
        if os.path.exists('libdpdk_capture.so'):
            self.logger.info("✓ DPDK library compiled")
            self.results['library'] = {'status': 'PASS'}
        else:
            self.logger.warning("⚠ DPDK library not found (run 'make' to compile)")
            self.results['library'] = {'status': 'WARNING', 'error': 'Library not compiled'}
            
    def test_permissions(self):
        """Test user permissions."""
        self.logger.info("Testing permissions...")
        
        if os.geteuid() == 0:
            self.logger.info("✓ Running as root (required for DPDK)")
            self.results['permissions'] = {'status': 'PASS'}
        else:
            self.logger.warning("⚠ Not running as root (required for DPDK operations)")
            self.results['permissions'] = {'status': 'WARNING', 'error': 'Not running as root'}
            
    def run_all_tests(self):
        """Run all system tests."""
        self.logger.info("Starting system verification tests...")
        
        test_methods = [
            self.test_python_dependencies,
            self.test_dpdk_installation,
            self.test_hugepages,
            self.test_vfio_driver,
            self.test_kafka_installation,
            self.test_kafka_services,
            self.test_network_interfaces,
            self.test_library_compilation,
            self.test_permissions
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.logger.error(f"Test failed: {test_method.__name__}: {e}")
                
        self.print_summary()
        
    def print_summary(self):
        """Print test results summary."""
        self.logger.info("\n" + "="*60)
        self.logger.info("SYSTEM VERIFICATION SUMMARY")
        self.logger.info("="*60)
        
        passed = 0
        failed = 0
        warnings = 0
        
        for test_name, result in self.results.items():
            status = result['status']
            if status == 'PASS':
                passed += 1
                status_symbol = "✓"
            elif status == 'FAIL':
                failed += 1
                status_symbol = "✗"
            else:  # WARNING
                warnings += 1
                status_symbol = "⚠"
                
            self.logger.info(f"{status_symbol} {test_name.replace('_', ' ').title()}: {status}")
            
        self.logger.info("-" * 60)
        self.logger.info(f"Results: {passed} passed, {failed} failed, {warnings} warnings")
        
        if failed > 0:
            self.logger.error("Some critical tests failed. Please fix these issues before running the application.")
            return False
        elif warnings > 0:
            self.logger.warning("Some tests have warnings. The application may still work.")
            return True
        else:
            self.logger.info("All tests passed! System is ready.")
            return True

def main():
    tester = SystemTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
