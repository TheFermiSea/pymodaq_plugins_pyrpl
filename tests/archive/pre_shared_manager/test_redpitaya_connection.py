#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Red Pitaya Connection Test Script

This script tests the connection to a Red Pitaya device and helps diagnose
connection issues before using the PyMoDAQ plugins.

Usage:
    python test_redpitaya_connection.py [hostname]
    
Example:
    python test_redpitaya_connection.py 100.107.106.75
"""

import sys
import time
import socket
import argparse


def test_network_ping(hostname):
    """Test basic network connectivity."""
    print(f"\n{'='*60}")
    print("TEST 1: Network Connectivity")
    print('='*60)
    
    try:
        print(f"Testing network connection to {hostname}...")
        
        # Try to resolve hostname
        try:
            ip = socket.gethostbyname(hostname)
            print(f"✓ DNS resolution successful: {hostname} -> {ip}")
        except socket.gaierror:
            print(f"✗ DNS resolution failed for {hostname}")
            return False
        
        # Try TCP connection to SSH port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        
        result = sock.connect_ex((hostname, 22))
        sock.close()
        
        if result == 0:
            print(f"✓ TCP connection to port 22 (SSH) successful")
            return True
        else:
            print(f"✗ Cannot connect to SSH port 22 (error code: {result})")
            return False
            
    except Exception as e:
        print(f"✗ Network test failed: {e}")
        return False


def test_ssh_connection(hostname):
    """Test SSH connection using paramiko."""
    print(f"\n{'='*60}")
    print("TEST 2: SSH Connection")
    print('='*60)
    
    try:
        import paramiko
    except ImportError:
        print("✗ paramiko not installed (required by PyRPL)")
        print("  Install with: pip install paramiko")
        return False
    
    try:
        print(f"Attempting SSH connection to {hostname}...")
        
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Default Red Pitaya credentials
        ssh.connect(
            hostname,
            port=22,
            username='root',
            password='root',
            timeout=10.0,
            banner_timeout=10.0,
            auth_timeout=10.0
        )
        
        print("✓ SSH authentication successful")
        
        # Test command execution
        stdin, stdout, stderr = ssh.exec_command('uname -a')
        output = stdout.read().decode('utf-8').strip()
        
        if 'Red Pitaya' in output or 'linux' in output.lower():
            print(f"✓ Command execution successful")
            print(f"  System: {output}")
        else:
            print(f"⚠ Command executed but unexpected output: {output}")
        
        ssh.close()
        return True
        
    except paramiko.AuthenticationException:
        print("✗ SSH authentication failed")
        print("  Default credentials (root/root) don't work")
        print("  Check if Red Pitaya password was changed")
        return False
        
    except paramiko.SSHException as e:
        print(f"✗ SSH error: {e}")
        return False
        
    except socket.timeout:
        print("✗ SSH connection timeout")
        print("  Red Pitaya is not responding within timeout")
        return False
        
    except Exception as e:
        print(f"✗ SSH connection failed: {e}")
        return False


def test_pyrpl_connection(hostname):
    """Test PyRPL connection with retry logic."""
    print(f"\n{'='*60}")
    print("TEST 3: PyRPL Connection")
    print('='*60)
    
    try:
        import pyrpl
    except ImportError:
        print("✗ pyrpl not installed")
        print("  Install with: pip install pyrpl")
        return False
    
    max_attempts = 2
    
    for attempt in range(max_attempts):
        try:
            if attempt > 0:
                print(f"\nRetry attempt {attempt + 1}/{max_attempts}...")
                time.sleep(3)
            
            print(f"Initializing PyRPL connection to {hostname}...")
            print("(This may take 10-30 seconds for FPGA bitstream upload...)")
            
            start_time = time.time()
            
            # Try to initialize PyRPL
            p = pyrpl.Pyrpl(
                hostname=hostname,
                config='connection_test',
                gui=False
            )
            
            elapsed = time.time() - start_time
            print(f"✓ PyRPL initialized successfully in {elapsed:.1f}s")
            
            # Test scope access
            print("Testing scope module access...")
            scope = p.rp.scope
            print(f"✓ Scope module accessible")
            
            # Clean up
            p.close()
            print("✓ Connection closed cleanly")
            
            return True
            
        except OSError as e:
            if 'Socket is closed' in str(e):
                print(f"✗ SSH socket closed during initialization")
                print(f"  Error: {e}")
                print("\n  Possible causes:")
                print("  1. Network instability or packet loss")
                print("  2. SSH connection timeout during FPGA upload")
                print("  3. Red Pitaya under heavy load")
                print("  4. Firewall or network settings")
                
                if attempt < max_attempts - 1:
                    print("\n  Retrying with longer timeout...")
                    continue
                else:
                    print("\n  SOLUTION: Try these steps:")
                    print("  - Check network stability (ping -c 20 100.107.106.75)")
                    print("  - Verify no other processes using Red Pitaya")
                    print("  - Try connecting via direct ethernet (avoid WiFi)")
                    print("  - Reboot Red Pitaya and try again")
                    return False
            else:
                print(f"✗ PyRPL connection failed: {e}")
                return False
        
        except TimeoutError as e:
            print(f"✗ Connection timeout: {e}")
            print("  Red Pitaya is not responding")
            return False
            
        except Exception as e:
            print(f"✗ PyRPL initialization failed: {e}")
            import traceback
            print("\nFull error:")
            traceback.print_exc()
            return False
    
    return False


def test_mock_mode():
    """Test that mock mode works."""
    print(f"\n{'='*60}")
    print("TEST 4: Mock Mode (No Hardware)")
    print('='*60)
    
    try:
        from pymodaq_plugins_pyrpl.utils.pyrpl_ipc_worker import pyrpl_worker_main
        from multiprocessing import Queue
        import multiprocessing
        
        print("Testing IPC worker in mock mode...")
        
        cmd_queue = Queue()
        resp_queue = Queue()
        
        config = {
            'hostname': '100.107.106.75',
            'config_name': 'test',
            'mock_mode': True
        }
        
        worker = multiprocessing.Process(
            target=pyrpl_worker_main,
            args=(cmd_queue, resp_queue, config),
            daemon=True
        )
        worker.start()
        
        # Wait for init
        response = resp_queue.get(timeout=5.0)
        
        if response['status'] == 'ok':
            print("✓ Mock mode worker initialized")
            
            # Test ping
            cmd_queue.put({'command': 'ping', 'params': {}})
            response = resp_queue.get(timeout=2.0)
            
            if response['data'] == 'pong':
                print("✓ Mock mode commands working")
            
            # Shutdown
            cmd_queue.put({'command': 'shutdown', 'params': {}})
            worker.join(timeout=3.0)
            
            print("✓ Mock mode test passed")
            return True
        else:
            print(f"✗ Mock mode initialization failed: {response}")
            return False
            
    except Exception as e:
        print(f"✗ Mock mode test failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Test Red Pitaya connection for PyMoDAQ-PyRPL plugins'
    )
    parser.add_argument(
        'hostname',
        nargs='?',
        default='100.107.106.75',
        help='Red Pitaya hostname or IP address (default: 100.107.106.75)'
    )
    parser.add_argument(
        '--skip-pyrpl',
        action='store_true',
        help='Skip PyRPL connection test (faster)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("Red Pitaya Connection Test Suite")
    print("="*60)
    print(f"\nTarget: {args.hostname}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test 1: Network
    results.append(("Network Connectivity", test_network_ping(args.hostname)))
    
    # Test 2: SSH
    if results[-1][1]:  # Only if network test passed
        results.append(("SSH Connection", test_ssh_connection(args.hostname)))
    else:
        print("\nSkipping SSH test (network test failed)")
        results.append(("SSH Connection", False))
    
    # Test 3: PyRPL (optional)
    if not args.skip_pyrpl:
        if results[-1][1]:  # Only if SSH test passed
            results.append(("PyRPL Connection", test_pyrpl_connection(args.hostname)))
        else:
            print("\nSkipping PyRPL test (SSH test failed)")
            results.append(("PyRPL Connection", False))
    
    # Test 4: Mock mode (always run)
    results.append(("Mock Mode", test_mock_mode()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:<30} {status}")
        if not passed and name != "Mock Mode":
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n✓ All tests passed! Red Pitaya is ready for PyMoDAQ plugins.")
        print("\nYou can now:")
        print("1. Launch PyMoDAQ dashboard")
        print("2. Add PyRPL plugins (Scope, PID, ASG, IQ)")
        print("3. Configure hostname: " + args.hostname)
        print("4. Initialize and start acquiring data")
        return 0
    else:
        print("\n✗ Some tests failed. See above for details.")
        print("\nRecommended actions:")
        print("1. Fix network/SSH connectivity issues")
        print("2. Reboot Red Pitaya if needed")
        print("3. Try direct ethernet connection")
        print("4. Use mock mode for development (enable in plugin settings)")
        return 1


if __name__ == '__main__':
    sys.exit(main())
