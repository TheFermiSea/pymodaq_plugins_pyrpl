#!/bin/bash
# Red Pitaya Unminimize Recovery Script
# Run this script sections manually by SSH'ing to root@rp-f08d6c.local (password: admin)

echo "🔧 Red Pitaya Unminimize Recovery Guide"
echo "======================================"
echo ""
echo "SSH into your Red Pitaya first:"
echo "ssh root@rp-f08d6c.local"
echo "Password: admin"
echo ""
echo "Then run these commands section by section:"
echo ""

echo "# ================================================"
echo "# SECTION 1: ASSESS DAMAGE"
echo "# ================================================"
cat << 'EOF'

# Check storage space (critical - should show available space)
df -h

# Check memory usage
free -m

# Check if Red Pitaya services are running
systemctl status redpitaya_discovery
systemctl status redpitaya_scpi

# Check if unminimize is still running
ps aux | grep -i unminimize

# Check what got installed by unminimize
apt list --installed | grep -E "(man-db|vim|nano|documentation|info)" | wc -l

# Check FPGA status
ls -la /opt/redpitaya/fpga/
cat /proc/modules | grep fpga

EOF

echo ""
echo "# ================================================"
echo "# SECTION 2: EMERGENCY CLEANUP (if storage full)"
echo "# ================================================"
cat << 'EOF'

# Stop any running unminimize processes
pkill -f unminimize

# Stop problematic services that eat resources
systemctl stop man-db.service man-db.timer apt-daily.service apt-daily-upgrade.service 2>/dev/null

# Clean package cache immediately
apt clean

# Remove large documentation packages installed by unminimize
apt remove --purge man-db manpages manpages-dev info vim vim-common nano -y

# Clean up
apt autoremove -y
apt autoclean

EOF

echo ""
echo "# ================================================"
echo "# SECTION 3: RESTORE RED PITAYA FUNCTIONALITY"
echo "# ================================================"
cat << 'EOF'

# Restart Red Pitaya core services
systemctl restart redpitaya_discovery
systemctl restart redpitaya_scpi

# Reload FPGA bitstream (critical for PyRPL)
cat /opt/redpitaya/fpga/fpga_0.94.bit > /dev/xdevcfg

# Kill any remaining problematic processes
pkill -f monitor
pkill -f pyrpl

# Test FPGA communication
/opt/redpitaya/bin/monitor 0x40000000

EOF

echo ""
echo "# ================================================"
echo "# SECTION 4: VERIFY RECOVERY"
echo "# ================================================"
cat << 'EOF'

# Check system health
df -h
free -m

# Test Red Pitaya services
systemctl status redpitaya_discovery
systemctl status redpitaya_scpi

# Test FPGA register access
/opt/redpitaya/bin/monitor 0x40100014

# Test web interface
curl -I http://localhost/ 2>/dev/null || echo "Web interface may need restart"

# Check if PyRPL server port is available
netstat -ln | grep :2222 || echo "PyRPL port ready"

EOF

echo ""
echo "# ================================================"
echo "# SECTION 5: FINAL REBOOT (RECOMMENDED)"
echo "# ================================================"
cat << 'EOF'

# Safest option - full reboot to ensure clean state
echo "Rebooting Red Pitaya to ensure clean state..."
reboot

# Wait 60 seconds, then test PyRPL connection:
# python -c "import pyrpl; rp = pyrpl.Pyrpl(hostname='rp-f08d6c.local', config='recovery_test', gui=False)"

EOF

echo ""
echo "🎯 PRIORITY ACTIONS:"
echo "1. Check storage space with 'df -h' - if >90% full, run cleanup immediately"
echo "2. Stop unminimize if still running with 'pkill -f unminimize'"
echo "3. Restart Red Pitaya services and reload FPGA bitstream"
echo "4. Reboot for clean recovery"
echo ""
echo "After recovery, the PyRPL connection should work properly!"

# Create a one-liner recovery command
echo ""
echo "# ================================================"
echo "# QUICK ONE-LINER RECOVERY (if system responsive)"
echo "# ================================================"
cat << 'EOF'

# Copy and paste this single command for quick recovery:
pkill -f unminimize; systemctl stop man-db.service man-db.timer; apt clean; apt remove --purge man-db manpages vim nano -y; apt autoremove -y; systemctl restart redpitaya_discovery redpitaya_scpi; cat /opt/redpitaya/fpga/fpga_0.94.bit > /dev/xdevcfg; reboot

EOF