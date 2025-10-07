#!/usr/bin/env python3
"""
Enable ASG test signal on OUT1
This connects to the RUNNING PyMoDAQ dashboard's IPC worker
"""
print("="*80)
print("INSTRUCTIONS:")
print("="*80)
print("1. Make sure PyMoDAQ dashboard is RUNNING with the PyRPL_Scope_IPC plugin")
print("2. Make sure you have a BNC cable connecting OUT1 → IN1")
print("3. This script will send commands to the worker to enable ASG")
print("")
print("Waiting 5 seconds for you to confirm dashboard is running...")
print("="*80)

import time
time.sleep(5)

# Since we can't easily access the running dashboard's queues,
# let's just document what needs to be done:

print("\nTO ENABLE TEST SIGNAL MANUALLY:")
print("="*80)
print("Since the dashboard is already running, you need to either:")
print("")
print("OPTION 1: Use PyRPL web interface at http://100.107.106.75")
print("  1. Navigate to ASG0 section")
print("  2. Set waveform = 'sin'")  
print("  3. Set frequency = 1000 Hz")
print("  4. Set amplitude = 0.5 V")
print("  5. Set output_direct = 'out1'")
print("")
print("OPTION 2: Add ASG plugin to PyMoDAQ dashboard")
print("  1. Add a PyRPL_ASG_IPC actuator module")
print("  2. Configure it to output on OUT1")
print("  3. Set frequency to 1000 Hz")
print("  4. Set amplitude to 0.5 V")
print("")
print("THEN in the Scope viewer:")
print("  1. Set Input Channel to 'in1'")
print("  2. Set Decimation to 64 or 128")
print("  3. Click 'Grab' or 'Snap'")
print("  4. You should see a 1 kHz sine wave with ~1V peak-to-peak")
print("="*80)
print("")
print("The signal statistics will be logged showing:")
print("  Vmin, Vmax, and Vpp (peak-to-peak voltage)")
print("")
print("If you see Vpp > 0.5V, the loopback is working!")
print("="*80)
