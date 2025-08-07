#!/usr/bin/env python3
"""
Connect to Red Pitaya via USB serial to get IP address and network info
"""
import serial
import time
import re

def connect_red_pitaya_serial():
    """Connect to Red Pitaya via ttyUSB2 and get network information"""
    print("="*60)
    print("Connecting to Red Pitaya via USB Serial (ttyUSB2)")
    print("="*60)
    
    try:
        # Open serial connection to Red Pitaya
        # Red Pitaya typically uses 115200 baud rate
        ser = serial.Serial('/dev/ttyUSB2', 115200, timeout=5)
        print(f"✅ Serial connection opened: {ser.port}")
        print(f"✅ Baud rate: {ser.baudrate}")
        
        # Give it a moment to initialize
        time.sleep(1)
        
        # Clear any existing data
        ser.flushInput()
        ser.flushOutput()
        
        # Send newline to get prompt
        print(f"\n🔍 Attempting to get shell prompt...")
        ser.write(b'\r\n')
        time.sleep(1)
        
        # Try to get a response
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            print(f"Initial response: {repr(response)}")
        
        # Send commands to get network info
        commands = [
            ('hostname', 'hostname'),
            ('ip_addr', 'ip addr show'),
            ('ifconfig', 'ifconfig'),
            ('route', 'ip route'),
            ('eth0_status', 'cat /sys/class/net/eth0/operstate'),
        ]
        
        results = {}
        
        for cmd_name, command in commands:
            print(f"\n📡 Sending command: {command}")
            
            # Send command
            ser.write(f'{command}\r\n'.encode())
            time.sleep(2)  # Wait for command to execute
            
            # Read response
            response = ""
            timeout_count = 0
            while timeout_count < 10:  # Max 5 seconds
                if ser.in_waiting > 0:
                    chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    response += chunk
                    timeout_count = 0
                else:
                    time.sleep(0.5)
                    timeout_count += 1
            
            results[cmd_name] = response.strip()
            print(f"Response length: {len(response)} chars")
            if response.strip():
                print(f"Response preview: {response[:200]}...")
        
        ser.close()
        print(f"\n✅ Serial connection closed")
        
        return results
        
    except serial.SerialException as e:
        print(f"❌ Serial connection failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None

def parse_network_info(results):
    """Parse network information from command results"""
    print(f"\n" + "="*60)
    print("Parsing Network Information")
    print("="*60)
    
    if not results:
        print("❌ No results to parse")
        return None
    
    network_info = {}
    
    # Parse hostname
    if 'hostname' in results and results['hostname']:
        hostname_match = re.search(r'([a-zA-Z0-9\-\.]+)', results['hostname'])
        if hostname_match:
            network_info['hostname'] = hostname_match.group(1)
            print(f"✅ Hostname: {network_info['hostname']}")
    
    # Parse IP addresses from ip addr or ifconfig
    ip_text = results.get('ip_addr', '') + ' ' + results.get('ifconfig', '')
    
    # Look for IPv4 addresses (not localhost)
    ip_pattern = r'inet (\d+\.\d+\.\d+\.\d+)/?\d*'
    ip_matches = re.findall(ip_pattern, ip_text)
    
    valid_ips = []
    for ip in ip_matches:
        if not ip.startswith('127.') and not ip.startswith('169.254'):
            valid_ips.append(ip)
    
    if valid_ips:
        network_info['ip_addresses'] = valid_ips
        print(f"✅ IP Addresses: {', '.join(valid_ips)}")
        
        # Primary IP (usually the first non-loopback)
        network_info['primary_ip'] = valid_ips[0]
        print(f"✅ Primary IP: {network_info['primary_ip']}")
    
    # Parse gateway from route
    if 'route' in results:
        gateway_match = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', results['route'])
        if gateway_match:
            network_info['gateway'] = gateway_match.group(1)
            print(f"✅ Gateway: {network_info['gateway']}")
    
    return network_info

def test_discovered_ip(ip_address):
    """Test the discovered IP address for PyRPL connectivity"""
    print(f"\n" + "="*60)
    print(f"Testing Discovered IP: {ip_address}")
    print("="*60)
    
    # Test ping
    import subprocess
    try:
        result = subprocess.run(['ping', '-c', '1', '-W', '2', ip_address], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Ping successful to {ip_address}")
        else:
            print(f"❌ Ping failed to {ip_address}")
    except Exception as e:
        print(f"⚠️ Ping test error: {e}")
    
    # Test PyRPL connection with the new IP
    try:
        import collections.abc
        import collections
        if not hasattr(collections, 'Mapping'):
            collections.Mapping = collections.abc.Mapping
            collections.MutableMapping = collections.abc.MutableMapping
        
        import pyrpl
        print(f"🔍 Attempting PyRPL connection to {ip_address}...")
        
        # Try PyRPL connection with short timeout
        rp = pyrpl.Pyrpl(hostname=ip_address, config='serial_discovery_test')
        print(f"🎉 PyRPL connection successful to {ip_address}!")
        
        # Test basic functionality
        try:
            voltage = rp.rp.sampler.in1
            print(f"✅ Voltage reading successful: IN1 = {voltage:.3f}V")
        except Exception as e:
            print(f"⚠️ Voltage reading failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ PyRPL connection failed: {e}")
        return False

def main():
    """Main function to discover Red Pitaya IP via serial"""
    print("Red Pitaya Serial IP Discovery")
    print("=" * 60)
    
    # Connect via serial and get network info
    results = connect_red_pitaya_serial()
    
    if results:
        # Parse the network information
        network_info = parse_network_info(results)
        
        if network_info and 'primary_ip' in network_info:
            ip_address = network_info['primary_ip']
            print(f"\n🎯 Discovered Red Pitaya IP: {ip_address}")
            
            # Test the discovered IP
            if test_discovered_ip(ip_address):
                print(f"\n🎉 SUCCESS! Red Pitaya fully accessible at {ip_address}")
                print(f"✅ Use this IP for PyRPL connections: {ip_address}")
            else:
                print(f"\n⚠️ IP discovered but PyRPL connection needs configuration")
                print(f"💡 Try configuring SSH access on Red Pitaya")
        else:
            print(f"\n❌ Could not extract IP address from serial communication")
            print(f"Raw results available for manual analysis")
            
            # Show raw results for debugging
            for cmd, result in results.items():
                if result.strip():
                    print(f"\n--- {cmd} ---")
                    print(result[:500] + "..." if len(result) > 500 else result)
    else:
        print(f"\n❌ Serial communication failed")
        print(f"💡 Check that Red Pitaya is powered and USB connection is secure")

if __name__ == '__main__':
    main()