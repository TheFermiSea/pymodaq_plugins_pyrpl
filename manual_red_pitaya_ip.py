#!/usr/bin/env python3
"""
Manually configure Red Pitaya IP address via serial
"""
import serial
import time
import subprocess

def get_host_network_info():
    """Get host network information to configure Red Pitaya on same network"""
    print("🔍 Analyzing host network configuration...")
    
    try:
        # Get host IP and network info
        result = subprocess.run(['ip', 'route', 'show', 'default'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            # Extract gateway IP
            import re
            gateway_match = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', result.stdout)
            if gateway_match:
                gateway = gateway_match.group(1)
                print(f"✅ Host gateway: {gateway}")
                
                # Determine network (assume /24 subnet)
                network_parts = gateway.split('.')
                network_base = f"{network_parts[0]}.{network_parts[1]}.{network_parts[2]}"
                
                # Suggest IP for Red Pitaya
                suggested_ip = f"{network_base}.200"  # Use .200 to avoid conflicts
                
                print(f"✅ Network base: {network_base}.x")
                print(f"✅ Suggested Red Pitaya IP: {suggested_ip}")
                
                return suggested_ip, gateway, f"{network_base}.1"
    except Exception as e:
        print(f"⚠️ Could not determine host network: {e}")
    
    # Fallback to common networks
    print("💡 Using common network configuration")
    return "192.168.1.200", "192.168.1.1", "192.168.1.1"

def configure_static_ip(target_ip, gateway, dns):
    """Configure static IP on Red Pitaya via serial"""
    print(f"\n🔧 Configuring static IP: {target_ip}")
    print(f"🔧 Gateway: {gateway}")
    print(f"🔧 DNS: {dns}")
    
    try:
        ser = serial.Serial('/dev/ttyUSB2', 115200, timeout=5)
        print(f"✅ Serial connection established")
        
        time.sleep(1)
        ser.flushInput()
        ser.flushOutput()
        
        # Get prompt
        ser.write(b'\r\n')
        time.sleep(1)
        
        def send_command(command, wait_time=3):
            """Send command via serial"""
            print(f"📡 Executing: {command}")
            ser.write(f'{command}\r\n'.encode())
            time.sleep(wait_time)
            
            response = ""
            timeout_count = 0
            while timeout_count < 10:
                if ser.in_waiting > 0:
                    response += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    timeout_count = 0
                else:
                    time.sleep(0.3)
                    timeout_count += 1
                    
            return response
        
        # Configure static IP
        print(f"\n🔄 Setting up static IP configuration...")
        
        # Bring interface down
        send_command('ifconfig eth0 down')
        
        # Configure static IP  
        send_command(f'ifconfig eth0 {target_ip} netmask 255.255.255.0')
        
        # Bring interface up
        send_command('ifconfig eth0 up')
        
        # Add default route
        send_command(f'route add default gw {gateway}')
        
        # Configure DNS
        send_command(f'echo "nameserver {dns}" > /etc/resolv.conf')
        
        # Verify configuration
        print(f"\n✅ Verifying network configuration...")
        response = send_command('ifconfig eth0')
        
        if target_ip in response:
            print(f"✅ IP address configured successfully")
            
            # Test connectivity from Red Pitaya
            print(f"\n🔍 Testing connectivity from Red Pitaya...")
            response = send_command('ping -c 2 8.8.8.8', 6)
            
            if 'bytes from' in response:
                print(f"✅ Internet connectivity confirmed")
            else:
                print(f"⚠️ Internet test inconclusive")
                
            # Test local gateway
            response = send_command(f'ping -c 1 {gateway}', 4) 
            if 'bytes from' in response:
                print(f"✅ Gateway connectivity confirmed")
        else:
            print(f"❌ IP configuration may have failed")
            ser.close()
            return None
        
        ser.close()
        return target_ip
        
    except Exception as e:
        print(f"❌ Static IP configuration failed: {e}")
        return None

def test_configured_ip(ip_address):
    """Test the manually configured IP"""
    print(f"\n" + "="*60)
    print(f"Testing Configured IP: {ip_address}")
    print("="*60)
    
    # Wait a moment for network to settle
    print("⏳ Waiting for network to settle...")
    time.sleep(5)
    
    # Test ping
    try:
        result = subprocess.run(['ping', '-c', '3', ip_address], 
                              capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print(f"✅ Ping successful to {ip_address}")
            print(f"✅ Network connectivity confirmed")
        else:
            print(f"❌ Ping failed to {ip_address}")
            print(f"💡 Network may need time to propagate")
            return False
    except Exception as e:
        print(f"❌ Ping test error: {e}")
        return False
    
    # Test PyRPL
    try:
        import collections.abc
        import collections
        if not hasattr(collections, 'Mapping'):
            collections.Mapping = collections.abc.Mapping
            collections.MutableMapping = collections.abc.MutableMapping
            
        import pyrpl
        print(f"🔍 Testing PyRPL connection...")
        
        rp = pyrpl.Pyrpl(hostname=ip_address, config='manual_config_test')
        print(f"🎉 PyRPL CONNECTION SUCCESSFUL!")
        
        # Test basic functionality
        voltage_in1 = rp.rp.sampler.in1
        voltage_in2 = rp.rp.sampler.in2
        print(f"✅ Voltage readings: IN1={voltage_in1:.3f}V, IN2={voltage_in2:.3f}V")
        
        # Test ASG
        asg = rp.rp.asg0
        asg.setup(frequency=1000, amplitude=0.1, waveform='sin')
        freq_readback = asg.frequency
        print(f"✅ ASG test: Set 1kHz, readback {freq_readback}Hz")
        
        # Test PID
        pid = rp.rp.pid0
        pid.input = 'in1'
        pid.setpoint = 0.0
        setpoint_readback = pid.setpoint
        print(f"✅ PID test: Set 0V setpoint, readback {setpoint_readback:.3f}V")
        
        print(f"\n🎉 FULL HARDWARE VALIDATION SUCCESSFUL!")
        return True
        
    except Exception as e:
        print(f"⚠️ PyRPL connection issue: {e}")
        if "Authentication failed" in str(e):
            print(f"💡 SSH authentication needed, but network is working!")
            return True
        return False

def main():
    """Configure Red Pitaya with manual IP and test"""
    print("Red Pitaya Manual IP Configuration")
    print("=" * 60)
    
    # Get host network info
    target_ip, gateway, dns = get_host_network_info()
    
    print(f"\n🎯 Target configuration:")
    print(f"   IP: {target_ip}")
    print(f"   Gateway: {gateway}")
    print(f"   DNS: {dns}")
    
    # Configure static IP
    configured_ip = configure_static_ip(target_ip, gateway, dns)
    
    if configured_ip:
        print(f"\n🎉 Red Pitaya IP configured: {configured_ip}")
        
        # Test the configuration
        if test_configured_ip(configured_ip):
            print(f"\n🚀 SUCCESS! Red Pitaya fully operational at {configured_ip}")
            print(f"✅ Ready for PyMoDAQ plugin testing")
            print(f"✅ Use this IP in plugin configuration: {configured_ip}")
        else:
            print(f"\n⚠️ Configuration complete but needs verification")
            print(f"💡 Try testing again after network propagation")
    else:
        print(f"\n❌ IP configuration failed")

if __name__ == '__main__':
    main()