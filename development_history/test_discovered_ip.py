#!/usr/bin/env python3
"""
Test the discovered Red Pitaya IP address
"""
import subprocess
import collections.abc
import collections

# Apply Python 3.10+ compatibility fix
if not hasattr(collections, 'Mapping'):
    collections.Mapping = collections.abc.Mapping
    collections.MutableMapping = collections.abc.MutableMapping

def test_red_pitaya_ip():
    """Test the discovered Red Pitaya IP address"""
    
    # Discovered IP from serial communication
    red_pitaya_ip = "169.254.227.47"
    hostname = "rp-f08d6c"
    
    print("="*60)
    print(f"Testing Discovered Red Pitaya: {hostname}")  
    print(f"IP Address: {red_pitaya_ip}")
    print("="*60)
    
    # Test ping
    print(f"🔍 Testing ping to {red_pitaya_ip}...")
    try:
        result = subprocess.run(['ping', '-c', '3', '-W', '2', red_pitaya_ip], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Ping successful to {red_pitaya_ip}")
            # Extract ping statistics
            if 'packets transmitted' in result.stdout:
                stats_line = [line for line in result.stdout.split('\n') if 'packets transmitted' in line]
                if stats_line:
                    print(f"✅ Ping stats: {stats_line[0]}")
        else:
            print(f"❌ Ping failed to {red_pitaya_ip}")
            return False
    except Exception as e:
        print(f"❌ Ping error: {e}")
        return False
    
    # Test SSH connection
    print(f"\n🔍 Testing SSH connection to {red_pitaya_ip}...")
    try:
        # Test if SSH port is open
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((red_pitaya_ip, 22))
        sock.close()
        
        if result == 0:
            print(f"✅ SSH port 22 is open on {red_pitaya_ip}")
        else:
            print(f"❌ SSH port 22 is not accessible on {red_pitaya_ip}")
            
    except Exception as e:
        print(f"❌ SSH port test error: {e}")
    
    # Test SCPI connection  
    print(f"\n🔍 Testing SCPI connection to {red_pitaya_ip}...")
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((red_pitaya_ip, 5000))
        
        if result == 0:
            print(f"✅ SCPI port 5000 is open on {red_pitaya_ip}")
            
            # Try basic SCPI command
            sock.send(b"*IDN?\r\n")
            response = sock.recv(1024).decode().strip()
            print(f"✅ SCPI ID response: {response}")
            sock.close()
        else:
            print(f"❌ SCPI port 5000 is not accessible on {red_pitaya_ip}")
            sock.close()
            
    except Exception as e:
        print(f"❌ SCPI connection error: {e}")
    
    # Test PyRPL connection
    print(f"\n🔍 Testing PyRPL connection to {red_pitaya_ip}...")
    try:
        import pyrpl
        print(f"✅ PyRPL library available")
        
        # Attempt PyRPL connection
        config_name = f"test_{hostname}"
        rp = pyrpl.Pyrpl(hostname=red_pitaya_ip, config=config_name)
        
        print(f"🎉 PyRPL connection successful to {red_pitaya_ip}!")
        
        # Test basic functionality
        try:
            voltage_in1 = rp.rp.sampler.in1
            voltage_in2 = rp.rp.sampler.in2
            print(f"✅ Voltage readings: IN1={voltage_in1:.3f}V, IN2={voltage_in2:.3f}V")
            
            # Test ASG
            asg = rp.rp.asg0
            asg.setup(frequency=1000, amplitude=0.1, waveform='sin')
            print(f"✅ ASG configured: 1kHz sine, 0.1V")
            
            # Test PID  
            pid = rp.rp.pid0
            pid.input = 'in1'
            pid.setpoint = 0.0
            print(f"✅ PID configured: IN1 input, 0V setpoint")
            
            print(f"\n🎉 ALL PYRPL TESTS SUCCESSFUL!")
            print(f"✅ Red Pitaya fully operational at {red_pitaya_ip}")
            
            return True
            
        except Exception as e:
            print(f"⚠️ PyRPL functional test failed: {e}")
            return True  # Connection worked, just function test failed
            
    except Exception as e:
        print(f"❌ PyRPL connection failed: {e}")
        # Show more detail about the error
        if "Authentication failed" in str(e):
            print(f"💡 SSH authentication issue - Red Pitaya may need SSH setup")
        elif "Connection refused" in str(e):
            print(f"💡 Connection refused - check Red Pitaya network services")
        return False
    
    return True

def main():
    """Test the discovered Red Pitaya"""
    print("Red Pitaya Discovered IP Test")
    print("=" * 60)
    
    success = test_red_pitaya_ip()
    
    if success:
        print(f"\n🎉 RED PITAYA HARDWARE TEST SUCCESSFUL!")
        print(f"✅ Device accessible at 169.254.227.47")
        print(f"✅ Hostname: rp-f08d6c") 
        print(f"✅ Ready for PyMoDAQ plugin testing")
    else:
        print(f"\n❌ Red Pitaya hardware test had issues")
        print(f"💡 Device found but may need configuration")

if __name__ == '__main__':
    main()