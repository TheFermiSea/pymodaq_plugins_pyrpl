# Red Pitaya Network Configuration Guide

## Working Configuration (Validated August 2025)

**Red Pitaya Address**: rp-f08d6c.local (192.168.1.150)
**Network**: Connected via router on 192.168.1.x subnet
**Connection Method**: SSH (port 22) via PyRPL library

## Network Discovery Method

The Red Pitaya was successfully discovered and configured using the USB serial connection method:

### USB Serial Configuration
1. **Physical Connection**: Red Pitaya connected via USB cable to ttyUSB2
2. **Serial Settings**: 115200 baud, 8N1  
3. **Access**: Direct console access to Red Pitaya Linux system

### Network Configuration Commands
```bash
# Access Red Pitaya via serial
screen /dev/ttyUSB2 115200

# Configure network (on Red Pitaya)
ifconfig eth0 192.168.1.150 netmask 255.255.255.0
route add default gw 192.168.1.1
echo "nameserver 8.8.8.8" > /etc/resolv.conf
```

### Validation Commands
```bash
# Test connectivity from host computer  
ping rp-f08d6c.local
ping 192.168.1.150

# Test SSH access (PyRPL requirement)
ssh root@rp-f08d6c.local  # Default: no password or 'root'
```

## PyRPL Connection Details

PyRPL uses SSH-based connection (not SCPI) with these parameters:
- **Hostname**: rp-f08d6c.local or 192.168.1.150
- **Port**: 22 (SSH)
- **Authentication**: Username/password (typically root with no password)
- **Timeout**: 10 seconds default

## Physical Setup

```
Host Computer (192.168.1.x) 
    ↓ (Ethernet via Router)
Router (192.168.1.1)
    ↓ (Ethernet)  
Red Pitaya (192.168.1.150 / rp-f08d6c.local)
    ↓ (USB Serial for configuration)
Host Computer (ttyUSB2)
```

## Signal Connections

For laser stabilization setup:
```
Laser → EOM → Optical Path → Photodiode → Red Pitaya IN1
                                            ↓
EOM Driver ← External Amplifier ← Red Pitaya OUT1
```

**Important Notes**:
- Red Pitaya operates at ±1V range
- Use external amplifiers/attenuators as needed
- Proper grounding essential for noise-free operation
- BNC cables recommended for analog connections

## Troubleshooting

### Connection Issues
- Verify Red Pitaya is on same subnet (192.168.1.x)
- Check router DHCP settings and reserved IP assignments
- Confirm SSH service is running on Red Pitaya
- Test with both hostname and IP address

### Network Configuration Persistence
- Red Pitaya network settings may reset on power cycle
- Consider adding network configuration to Red Pitaya startup scripts
- USB serial access always available for reconfiguration

### PyRPL Specific Issues  
- PyRPL requires SSH access (not HTTP/SCPI)
- Default PyRPL port is 2222 but can use standard SSH port 22
- Connection timeout should be set to at least 10 seconds
- Some PyRPL versions have connection stability issues - use wrapper retry logic

## Validated Hardware
- **Red Pitaya Model**: STEMlab (PyRPL compatible)
- **Firmware**: Standard Red Pitaya Linux image
- **PyRPL Version**: 0.9.5+ recommended
- **Test Date**: August 7, 2025
- **Connection Status**: Fully operational

This configuration has been validated for production use with the PyMoDAQ PyRPL plugin suite.