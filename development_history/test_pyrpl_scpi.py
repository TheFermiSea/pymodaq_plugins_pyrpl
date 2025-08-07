#!/usr/bin/env python3
"""
Test Red Pitaya SCPI connection (alternative to SSH)
"""
import socket
import time
import collections.abc
import collections

# Apply Python 3.10+ compatibility fix  
if not hasattr(collections, 'Mapping'):
    collections.Mapping = collections.abc.Mapping
    collections.MutableMapping = collections.abc.MutableMapping

def test_scpi_connection():
    """Test Red Pitaya SCPI connection"""
    print("="*60)
    print("Testing Red Pitaya SCPI Connection") 
    print("="*60)
    
    red_pitaya_ip = "192.168.1.100"
    scpi_port = 5000
    
    try:
        print(f"🔍 Connecting to SCPI server at {red_pitaya_ip}:{scpi_port}...")
        
        # Create socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)  # 5 second timeout
        
        # Connect to Red Pitaya SCPI server
        sock.connect((red_pitaya_ip, scpi_port))
        print(f"✅ SCPI connection established")
        
        # Test identification query
        sock.send(b"*IDN?\r\n")
        response = sock.recv(1024).decode().strip()
        print(f"✅ Device ID: {response}")
        
        # Test voltage reading
        sock.send(b"ACQ:SOUR1:VOLT?\r\n") 
        response = sock.recv(1024).decode().strip()
        print(f"✅ IN1 Voltage: {response}")
        
        # Test ASG (if available)
        try:
            sock.send(b"SOUR1:FUNC SIN\r\n")
            sock.send(b"SOUR1:FREQ:FIX 1000\r\n") 
            sock.send(b"SOUR1:VOLT 0.1\r\n")
            print(f"✅ ASG configured via SCPI: 1kHz, 0.1V sine wave")
        except Exception as e:
            print(f"⚠️ ASG SCPI commands failed: {e}")
        
        sock.close()
        print(f"✅ SCPI connection test successful!")
        return True
        
    except socket.timeout:
        print(f"❌ SCPI connection timeout - port {scpi_port} not responding")
        return False
    except ConnectionRefusedError:
        print(f"❌ SCPI connection refused - port {scpi_port} not open")
        return False  
    except Exception as e:
        print(f"❌ SCPI connection failed: {e}")
        return False

def test_web_interface():
    """Test Red Pitaya web interface"""
    print(f"\n" + "="*60)
    print("Testing Red Pitaya Web Interface")
    print("="*60)
    
    red_pitaya_ip = "192.168.1.100"
    
    try:
        import urllib.request
        import urllib.error
        
        url = f"http://{red_pitaya_ip}"
        print(f"🔍 Checking web interface at {url}...")
        
        request = urllib.request.Request(url, headers={
            'User-Agent': 'PyRPL-Test/1.0'
        })
        
        with urllib.request.urlopen(request, timeout=5) as response:
            content = response.read(200).decode('utf-8', errors='ignore')
            print(f"✅ Web interface accessible")
            print(f"✅ HTTP Status: {response.status}")
            
            if 'red pitaya' in content.lower() or 'stemlab' in content.lower():
                print(f"✅ Confirmed Red Pitaya device")
            else:
                print(f"⚠️ Web content doesn't clearly identify Red Pitaya")
                
            return True
            
    except urllib.error.URLError as e:
        print(f"❌ Web interface not accessible: {e}")
        return False
    except Exception as e:
        print(f"❌ Web interface test failed: {e}")
        return False

def main():
    """Run hardware connectivity tests"""
    print("Red Pitaya Hardware Connectivity Test")  
    print("=" * 60)
    
    # Test SCPI connection
    scpi_ok = test_scpi_connection()
    
    # Test web interface
    web_ok = test_web_interface()
    
    print(f"\n" + "="*60)
    print("Hardware Connectivity Results")
    print("="*60)
    print(f"SCPI Connection: {'✅ PASS' if scpi_ok else '❌ FAIL'}")
    print(f"Web Interface: {'✅ PASS' if web_ok else '❌ FAIL'}")
    
    if scpi_ok or web_ok:
        print(f"\n✅ Red Pitaya hardware is accessible!")
        print(f"✅ Device responding on network at 192.168.1.100")
        if scpi_ok:
            print(f"✅ SCPI interface available for direct control") 
        print(f"\nFor PyRPL SSH connection, you may need to:")
        print(f"1. Enable SSH on Red Pitaya")
        print(f"2. Configure SSH authentication")  
        print(f"3. Use default credentials (root/root)")
    else:
        print(f"\n❌ Red Pitaya hardware not accessible via SCPI or web")
        print(f"⚠️ Check device power and network configuration")

if __name__ == '__main__':
    main()