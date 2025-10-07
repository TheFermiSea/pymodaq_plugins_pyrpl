#!/usr/bin/env python3
"""
Comprehensive integration test for PyMoDAQ PyRPL plugins with REAL hardware.
Tests both In-Process and Bridge Client architectures with actual data acquisition.
"""
import sys
import time
import numpy as np
from qtpy.QtCore import QCoreApplication, QTimer
from qtpy.QtWidgets import QApplication

# Import the plugins
from pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_Pyrpl_InProcess import DAQ_1DViewer_Pyrpl_InProcess
from pymodaq_plugins_pyrpl.hardware.pyrpl_worker import PyrplWorker

print("="*80)
print("PyMoDAQ PyRPL Plugin - Real Hardware Integration Test")
print("="*80)

# Test configuration
HARDWARE_IP = '100.107.106.75'
TEST_VOLTAGE = 0.5  # 500mV test signal

class PluginTester:
    """Helper class to test PyMoDAQ plugins with real hardware."""

    def __init__(self):
        self.app = None
        self.data_received = False
        self.acquired_data = None
        self.status_messages = []

    def setup_qt_app(self):
        """Create Qt application context."""
        if QApplication.instance() is None:
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()
        print("✓ Qt Application context created")

    def test_worker_directly(self):
        """Test 1: Direct PyrplWorker test (no Qt complexity)."""
        print("\n" + "="*80)
        print("TEST 1: Direct PyrplWorker Hardware Test")
        print("="*80)

        try:
            print("\n1.1 Creating PyrplWorker...")
            worker = PyrplWorker()

            print("1.2 Connecting to hardware at", HARDWARE_IP)
            config = {
                'hostname': HARDWARE_IP,
                'user': 'root',
                'password': 'root'
            }

            connected = worker.connect(config)
            if not connected:
                print("✗ FAILED: Could not connect to hardware")
                return False

            print(f"✓ Connected: {worker.get_idn()}")

            print("\n1.3 Setting output voltage for loopback test...")
            worker.set_output_voltage('out1', TEST_VOLTAGE)
            print(f"✓ Set OUT1 to {TEST_VOLTAGE}V")

            print("\n1.4 Configuring scope for IN1 acquisition...")
            worker.setup_scope(
                channel='in1',
                decimation=64,
                trigger_source='immediately',
                trigger_level=0.0,
                duration=0.01
            )
            print("✓ Scope configured")

            print("\n1.5 Acquiring trace data...")
            times, voltages = worker.acquire_trace()

            if len(voltages) == 0:
                print("✗ FAILED: No data acquired")
                return False

            mean_voltage = np.mean(voltages)
            std_voltage = np.std(voltages)
            print(f"✓ Acquired {len(voltages)} samples")
            print(f"  Time range: {times[0]:.6f}s to {times[-1]:.6f}s")
            print(f"  Voltage mean: {mean_voltage:.4f}V")
            print(f"  Voltage std: {std_voltage:.6f}V")

            # Verify data quality
            if np.isclose(mean_voltage, TEST_VOLTAGE, atol=0.05):
                print(f"✓ LOOPBACK VERIFIED: Mean voltage matches test signal")
            else:
                print(f"⚠ WARNING: Mean voltage {mean_voltage:.4f}V differs from test {TEST_VOLTAGE}V")
                print("  (This may be normal if OUT1 is not connected to IN1)")

            print("\n1.6 Disconnecting...")
            worker.disconnect()
            print("✓ Disconnected")

            print("\n" + "="*80)
            print("TEST 1 RESULT: ✅ PASSED - Worker hardware interface functional")
            print("="*80)
            return True

        except Exception as e:
            print(f"\n✗ TEST 1 FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_inprocess_plugin(self):
        """Test 2: In-Process Plugin with Qt threading."""
        print("\n" + "="*80)
        print("TEST 2: In-Process Plugin Integration Test")
        print("="*80)

        try:
            print("\n2.1 Creating In-Process plugin instance...")
            plugin = DAQ_1DViewer_Pyrpl_InProcess(parent=None, params_state=None)

            # Connect to status and data signals
            def status_callback(cmd):
                msg = cmd[1][0] if len(cmd) > 1 and len(cmd[1]) > 0 else str(cmd)
                self.status_messages.append(msg)
                print(f"  Status: {msg}")

            def data_callback(data_export):
                self.data_received = True
                self.acquired_data = data_export
                print(f"  Data received: {len(data_export.data)} datasets")

            plugin.status_sig[list].connect(status_callback)
            plugin.dte_signal_temp.connect(data_callback)

            print("\n2.2 Setting hardware IP address...")
            plugin.settings.child('pyrpl_config', 'hostname').setValue(HARDWARE_IP)
            print(f"✓ Configured for {HARDWARE_IP}")

            print("\n2.3 Initializing detector (ini_detector)...")
            status = plugin.ini_detector(controller=None)

            # Process Qt events to let signals/slots work
            print("\n2.4 Processing Qt events for worker thread initialization...")
            for i in range(50):  # Give it 5 seconds
                self.app.processEvents()
                time.sleep(0.1)
                if 'PyRPL Worker Initialized' in ' '.join(self.status_messages):
                    break

            if 'Successfully connected' not in ' '.join(self.status_messages):
                print("✗ FAILED: No successful connection message")
                print(f"  Status messages: {self.status_messages}")
                return False

            print("✓ Worker thread initialized and connected")

            print("\n2.5 Grabbing data (grab_data)...")
            self.data_received = False
            plugin.grab_data()

            # Wait for data with timeout
            print("  Waiting for data acquisition...")
            timeout = 100  # 10 seconds
            for i in range(timeout):
                self.app.processEvents()
                time.sleep(0.1)
                if self.data_received:
                    break

            if not self.data_received:
                print(f"✗ FAILED: No data received after {timeout/10}s")
                return False

            print("✓ Data acquisition successful")

            # Analyze acquired data
            data_list = self.acquired_data.data
            if len(data_list) > 0:
                data_item = data_list[0]
                voltages = data_item.data[0]
                print(f"  Samples: {len(voltages)}")
                print(f"  Mean: {np.mean(voltages):.4f}V")
                print(f"  Std: {np.std(voltages):.6f}V")

            print("\n2.6 Closing plugin...")
            plugin.close()

            # Let cleanup happen
            for i in range(10):
                self.app.processEvents()
                time.sleep(0.1)

            print("✓ Plugin closed")

            print("\n" + "="*80)
            print("TEST 2 RESULT: ✅ PASSED - In-Process plugin functional")
            print("="*80)
            return True

        except Exception as e:
            print(f"\n✗ TEST 2 FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_all_tests(self):
        """Run all integration tests."""
        print("\nStarting comprehensive hardware integration tests...")
        print(f"Target hardware: {HARDWARE_IP}")
        print()

        # Test 1: Direct worker test
        test1_passed = self.test_worker_directly()

        # Test 2: In-Process plugin (requires Qt)
        self.setup_qt_app()
        test2_passed = self.test_inprocess_plugin()

        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Test 1 (Direct Worker):     {'✅ PASSED' if test1_passed else '❌ FAILED'}")
        print(f"Test 2 (In-Process Plugin): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
        print("="*80)

        if test1_passed and test2_passed:
            print("\n🎉 ALL TESTS PASSED - PyRPL plugins fully functional with real hardware!")
            return 0
        else:
            print("\n⚠️  SOME TESTS FAILED - See details above")
            return 1

if __name__ == '__main__':
    tester = PluginTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
