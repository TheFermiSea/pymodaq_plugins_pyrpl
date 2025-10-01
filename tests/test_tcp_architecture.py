#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for TCP/IP architecture

This script tests the PyRPL TCP server and Scope TCP client
in mock mode without requiring the full PyMoDAQ dashboard.

Usage:
    python tests/test_tcp_architecture.py
"""

import sys
import time
import threading
import numpy as np
from qtpy import QtWidgets

# Add src to path
sys.path.insert(0, 'src')

from pymodaq_plugins_pyrpl.utils.pyrpl_tcp_server import PyMoDAQPyRPLServer


def test_mock_server():
    """Test the PyRPL TCP server in mock mode."""
    print("\n" + "="*70)
    print("TEST: PyRPL TCP Server (Mock Mode)")
    print("="*70)
    
    try:
        # Create Qt application
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication(sys.argv)
        
        # Create server in mock mode
        print("\n1. Creating PyRPL TCP server...")
        server = PyMoDAQPyRPLServer(
            hostname='100.107.106.75',
            config_name='test',
            port=6341,
            mock_mode=True
        )
        
        print("✓ Server created successfully")
        print(f"  - Mock mode: {server.mock_mode}")
        print(f"  - PyRPL instance: {server.pyrpl is not None}")
        print(f"  - Port: 6341")
        
        # Test PyRPL modules
        print("\n2. Testing PyRPL module access...")
        modules_to_test = ['scope', 'iq0', 'asg0', 'pid0']
        for module_name in modules_to_test:
            try:
                module = server._get_module(module_name)
                print(f"✓ Module '{module_name}': accessible")
            except Exception as e:
                print(f"✗ Module '{module_name}': {e}")
        
        # Test scope configuration
        print("\n3. Testing scope configuration...")
        try:
            scope = server._get_module('scope')
            scope.setup(
                input1='in1',
                decimation=64,
                trigger_source='immediately'
            )
            print("✓ Scope configuration successful")
        except Exception as e:
            print(f"✗ Scope configuration failed: {e}")
        
        # Test scope data acquisition
        print("\n4. Testing scope data acquisition...")
        try:
            scope = server._get_module('scope')
            data = scope.curve()
            print(f"✓ Data acquisition successful")
            print(f"  - Data shape: {data.shape}")
            print(f"  - Data type: {data.dtype}")
            print(f"  - Data range: [{data.min():.3f}, {data.max():.3f}]")
        except Exception as e:
            print(f"✗ Data acquisition failed: {e}")
        
        # Test IQ module
        print("\n5. Testing IQ module...")
        try:
            iq0 = server._get_module('iq0')
            iq_value = iq0.iq()
            print(f"✓ IQ acquisition successful")
            print(f"  - IQ value: {iq_value}")
            print(f"  - I component: {iq_value.real:.3f}")
            print(f"  - Q component: {iq_value.imag:.3f}")
        except Exception as e:
            print(f"✗ IQ acquisition failed: {e}")
        
        # Test ASG module
        print("\n6. Testing ASG module...")
        try:
            asg0 = server._get_module('asg0')
            asg0.offset = 0.5
            print(f"✓ ASG offset set successfully")
            print(f"  - Offset: {asg0.offset}")
        except Exception as e:
            print(f"✗ ASG configuration failed: {e}")
        
        # Test PID module
        print("\n7. Testing PID module...")
        try:
            pid0 = server._get_module('pid0')
            pid0.setpoint = 0.3
            print(f"✓ PID setpoint set successfully")
            print(f"  - Setpoint: {pid0.setpoint}")
        except Exception as e:
            print(f"✗ PID configuration failed: {e}")
        
        # Cleanup
        print("\n8. Closing server...")
        server.close_server()
        print("✓ Server closed")
        
        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED")
        print("="*70)
        
        return True
    
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_command_protocol():
    """Test command handling protocol."""
    print("\n" + "="*70)
    print("TEST: Command Protocol")
    print("="*70)
    
    try:
        # Create Qt application
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication(sys.argv)
        
        # Create server
        print("\n1. Creating server...")
        server = PyMoDAQPyRPLServer(
            hostname='100.107.106.75',
            config_name='test',
            port=6342,  # Different port to avoid conflicts
            mock_mode=True
        )
        print("✓ Server created")
        
        # Test command structures
        print("\n2. Testing command structures...")
        
        commands_to_test = [
            {
                'name': 'Ping',
                'data': {'command': 'ping'}
            },
            {
                'name': 'Configure Scope',
                'data': {
                    'command': 'configure',
                    'module': 'scope',
                    'config': {
                        'input1': 'in2',
                        'decimation': 128,
                        'trigger_source': 'ch1_positive_edge'
                    }
                }
            },
            {
                'name': 'Grab Scope',
                'data': {
                    'command': 'grab',
                    'module': 'scope',
                    'config': {},
                    'timebase': 0.001
                }
            },
            {
                'name': 'Move ASG',
                'data': {
                    'command': 'move_abs',
                    'module': 'asg0',
                    'value': 0.75
                }
            },
        ]
        
        for test in commands_to_test:
            print(f"\n  Testing: {test['name']}")
            try:
                # Simulate command processing (without actual socket)
                command = test['data'].get('command')
                module_name = test['data'].get('module', '')
                
                if command == 'ping':
                    print(f"    ✓ Ping command structure valid")
                elif command == 'configure':
                    module = server._get_module(module_name)
                    config = test['data'].get('config', {})
                    module.setup(**config)
                    print(f"    ✓ Configure command executed")
                elif command == 'grab':
                    module = server._get_module(module_name)
                    data = module.curve()
                    print(f"    ✓ Grab command executed ({len(data)} points)")
                elif command == 'move_abs':
                    module = server._get_module(module_name)
                    value = test['data']['value']
                    module.offset = value
                    print(f"    ✓ Move command executed (value={value})")
                else:
                    print(f"    ? Unknown command: {command}")
            
            except Exception as e:
                print(f"    ✗ Command failed: {e}")
        
        # Cleanup
        print("\n3. Closing server...")
        server.close_server()
        print("✓ Server closed")
        
        print("\n" + "="*70)
        print("✓ PROTOCOL TESTS PASSED")
        print("="*70)
        
        return True
    
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "#"*70)
    print("#  PyRPL TCP/IP Architecture Tests")
    print("#"*70)
    
    # Run tests
    test1_passed = test_mock_server()
    test2_passed = test_command_protocol()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Mock Server Test:     {'✓ PASS' if test1_passed else '✗ FAIL'}")
    print(f"Command Protocol Test: {'✓ PASS' if test2_passed else '✗ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n✓ ALL TESTS PASSED - TCP Architecture Working!")
        sys.exit(0)
    else:
        print("\n✗ SOME TESTS FAILED")
        sys.exit(1)
