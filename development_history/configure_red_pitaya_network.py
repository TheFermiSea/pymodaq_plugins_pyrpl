#!/usr/bin/env python3
"""
Configure Red Pitaya network via serial connection
"""
import serial
import time
import re

def configure_red_pitaya_network():
    """Configure Red Pitaya network settings via serial"""
    print("="*60)
    print("Configuring Red Pitaya Network via Serial")
    print("="*60)
    
    try:
        # Open serial connection
        ser = serial.Serial('/dev/ttyUSB2', 115200, timeout=5)
        print(f"✅ Serial connection opened to {ser.port}")
        
        time.sleep(1)
        ser.flushInput()
        ser.flushOutput()
        
        # Get a fresh prompt
        ser.write(b'\r\n')
        time.sleep(1)
        
        def send_command(command, wait_time=2):
            """Send command and get response"""
            print(f"📡 Executing: {command}")
            ser.write(f'{command}\r\n'.encode())
            time.sleep(wait_time)
            
            response = ""
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            return response
        
        # Check current network status
        print(f"\n🔍 Checking current network status...")
        response = send_command('ip addr show eth0')
        print(f"Current eth0 status: {len(response)} chars received")
        
        # Check if DHCP client is running
        print(f"\n🔍 Checking DHCP client status...")
        response = send_command('ps aux | grep dhcp')
        if 'dhcp' in response.lower():
            print("✅ DHCP client appears to be running")
        else:
            print("⚠️ DHCP client may not be running")
        
        # Try to renew DHCP lease
        print(f"\n🔄 Attempting DHCP renewal...")
        send_command('dhclient -r eth0', 3)  # Release current lease
        send_command('dhclient eth0', 5)     # Request new lease
        
        # Check new IP address
        print(f"\n🔍 Checking new network configuration...")
        response = send_command('ip addr show eth0', 3)
        
        # Extract IP address from response
        ip_matches = re.findall(r'inet (\d+\.\d+\.\d+\.\d+)/\d+', response)
        valid_ips = [ip for ip in ip_matches if not ip.startswith('127.') and not ip.startswith('169.254')]
        
        if valid_ips:
            new_ip = valid_ips[0]
            print(f"🎉 New IP address obtained: {new_ip}")
            
            # Get gateway information
            response = send_command('ip route show default')
            gateway_match = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', response)
            if gateway_match:
                gateway = gateway_match.group(1)
                print(f"✅ Gateway: {gateway}")
            
            # Test connectivity
            print(f"\n🔍 Testing connectivity from Red Pitaya...")
            response = send_command(f'ping -c 2 8.8.8.8', 5)
            if 'bytes from' in response:
                print(f"✅ Internet connectivity confirmed")
            else:
                print(f"⚠️ Internet connectivity test unclear")
            
            ser.close()
            return new_ip
            
        else:
            print(f"❌ No valid IP address obtained")
            
            # Try alternative configuration
            print(f"\n🔄 Trying alternative network configuration...")
            
            # Check network interface status
            send_command('ifconfig eth0 up')
            time.sleep(2)
            
            # Try DHCP again with verbose output
            response = send_command('dhclient -v eth0', 8)
            print(f"DHCP verbose response: {len(response)} chars")
            
            # Final check
            response = send_command('ip addr show eth0')
            ip_matches = re.findall(r'inet (\d+\.\d+\.\d+\.\d+)/\d+', response)
            valid_ips = [ip for ip in ip_matches if not ip.startswith('127.') and not ip.startswith('169.254')]
            
            if valid_ips:
                new_ip = valid_ips[0]
                print(f"🎉 IP address obtained after retry: {new_ip}")
                ser.close()
                return new_ip
            else:
                print(f"❌ Still no valid IP address")
                ser.close()
                return None
        
    except Exception as e:
        print(f"❌ Network configuration failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_new_ip(ip_address):
    """Test the newly configured IP address"""
    if not ip_address:
        return False
        
    print(f"\n" + "="*60)
    print(f"Testing New IP Address: {ip_address}")
    print("="*60)
    
    # Test ping
    import subprocess
    try:
        result = subprocess.run(['ping', '-c', '3', ip_address], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Ping successful to {ip_address}")
        else:
            print(f"❌ Ping failed to {ip_address}")
            return False
    except Exception as e:
        print(f"❌ Ping test failed: {e}")
        return False
    
    # Test PyRPL connection
    try:
        import collections.abc
        import collections
        if not hasattr(collections, 'Mapping'):
            collections.Mapping = collections.abc.Mapping
            collections.MutableMapping = collections.abc.MutableMapping
            
        import pyrpl
        print(f"🔍 Testing PyRPL connection to {ip_address}...")
        
        rp = pyrpl.Pyrpl(hostname=ip_address, config='network_test')
        print(f"🎉 PyRPL connection successful!")
        
        # Quick functionality test
        voltage = rp.rp.sampler.in1
        print(f"✅ Voltage reading: IN1 = {voltage:.3f}V")
        
        return True
        
    except Exception as e:
        print(f"⚠️ PyRPL test: {e}")
        if "Authentication failed" in str(e):
            print(f"💡 PyRPL connection blocked by SSH authentication")
            print(f"💡 But network connectivity is confirmed!")
            return True  # Network is working
        return False

def main():
    """Configure Red Pitaya network and test"""
    print("Red Pitaya Network Configuration")
    print("=" * 60)
    
    # Configure network
    new_ip = configure_red_pitaya_network()
    
    if new_ip:
        print(f"\n🎯 Red Pitaya configured with IP: {new_ip}")
        
        # Test the new IP
        if test_new_ip(new_ip):
            print(f"\n🎉 SUCCESS! Red Pitaya accessible at {new_ip}")
            print(f"✅ Update your PyRPL plugins to use IP: {new_ip}")
            print(f"✅ Network configuration complete")
        else:
            print(f"\n⚠️ IP configured but connectivity needs verification")
    else:
        print(f"\n❌ Network configuration failed")
        print(f"💡 Red Pitaya may need manual network setup")

if __name__ == '__main__':
    main()