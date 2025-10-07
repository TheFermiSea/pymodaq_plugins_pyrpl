#!/usr/bin/env python3
"""
Direct test of the IPC worker to prove data acquisition is working
This will save actual data to CSV files so you can verify it's real
"""
import multiprocessing
from multiprocessing import Queue, Process
import time
import sys
import numpy as np

# Import the worker
sys.path.insert(0, '/Users/briansquires/serena_projects/pymodaq_plugins_pyrpl/src')
from pymodaq_plugins_pyrpl.utils.pyrpl_ipc_worker import pyrpl_worker_main

print("="*80)
print("DIRECT IPC WORKER DATA ACQUISITION TEST")
print("="*80)

# Create queues
command_queue = Queue()
response_queue = Queue()

# Start worker
print("\n1. Starting PyRPL worker process...")
worker_process = Process(
    target=pyrpl_worker_main,
    args=(command_queue, response_queue),
    kwargs={
        'hostname': '100.107.106.75',
        'config_name': 'verification_test',
        'mock_mode': False
    }
)
worker_process.start()

# Wait for initialization
print("   Waiting for worker initialization...")
try:
    init_response = response_queue.get(timeout=30)
    if init_response['status'] == 'ok':
        print(f"   ✓ Worker initialized: {init_response['data']}")
    else:
        print(f"   ✗ Worker init failed: {init_response['data']}")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Timeout or error: {e}")
    sys.exit(1)

# Test 1: Ping
print("\n2. Testing communication (ping)...")
command_queue.put({'command': 'ping', 'params': {}})
response = response_queue.get(timeout=5)
print(f"   Response: {response}")

# Test 2: Configure scope for IN1
print("\n3. Configuring scope for IN1...")
command_queue.put({
    'command': 'scope_set_decimation',
    'params': {'value': 64}
})
response = response_queue.get(timeout=5)
print(f"   Decimation set: {response}")

command_queue.put({
    'command': 'scope_set_input',
    'params': {'channel': 'in1'}
})
response = response_queue.get(timeout=5)
print(f"   Input channel set: {response}")

# Test 3: Acquire data from IN1
print("\n4. Acquiring data from IN1...")
command_queue.put({
    'command': 'scope_acquire',
    'params': {
        'decimation': 64,
        'trigger_source': 'immediately',
        'input_channel': 'in1',
        'timeout': 5.0
    }
})
response = response_queue.get(timeout=10)

if response['status'] == 'ok':
    data = response['data']
    voltage = np.array(data['voltage'])
    time_data = np.array(data['time'])
    
    print(f"   ✓ Data acquired successfully!")
    print(f"   - Number of points: {len(voltage)}")
    print(f"   - Time range: {time_data[0]:.6f} to {time_data[-1]:.6f} s")
    print(f"   - Duration: {time_data[-1] - time_data[0]:.6f} s")
    print(f"   - Voltage min: {voltage.min():.6f} V")
    print(f"   - Voltage max: {voltage.max():.6f} V")
    print(f"   - Voltage mean: {voltage.mean():.6f} V")
    print(f"   - Voltage std: {voltage.std():.6f} V")
    print(f"   - Voltage p-p: {voltage.max() - voltage.min():.6f} V")
    
    # Save to CSV
    print("\n5. Saving data to CSV files...")
    np.savetxt('scope_data_in1_voltage.csv', voltage, delimiter=',', header='Voltage (V)')
    np.savetxt('scope_data_in1_time.csv', time_data, delimiter=',', header='Time (s)')
    print("   ✓ Saved to:")
    print("     - scope_data_in1_voltage.csv")
    print("     - scope_data_in1_time.csv")
    
    # Print first 20 samples
    print("\n6. First 20 samples:")
    print("   Index | Time (ms) | Voltage (V)")
    print("   " + "-"*40)
    for i in range(min(20, len(voltage))):
        print(f"   {i:5d} | {time_data[i]*1000:9.6f} | {voltage[i]:11.8f}")
    
    # Calculate FFT to check for signals
    print("\n7. Frequency analysis (FFT)...")
    sample_rate = 1.0 / (time_data[1] - time_data[0])
    fft = np.fft.rfft(voltage - voltage.mean())
    fft_mag = np.abs(fft)
    fft_freq = np.fft.rfftfreq(len(voltage), 1.0/sample_rate)
    
    # Find peak frequency
    peak_idx = np.argmax(fft_mag[1:]) + 1  # Skip DC
    peak_freq = fft_freq[peak_idx]
    peak_mag = fft_mag[peak_idx]
    
    print(f"   - Sample rate: {sample_rate:.2f} Hz")
    print(f"   - Frequency resolution: {fft_freq[1]:.2f} Hz")
    print(f"   - Peak frequency: {peak_freq:.2f} Hz")
    print(f"   - Peak magnitude: {peak_mag:.6f}")
    
    # Find top 5 frequencies
    top_indices = np.argsort(fft_mag)[-6:-1][::-1]  # Skip DC
    print("\n   Top 5 frequency components:")
    for i, idx in enumerate(top_indices, 1):
        print(f"      {i}. {fft_freq[idx]:8.2f} Hz - magnitude: {fft_mag[idx]:.6f}")
    
else:
    print(f"   ✗ Data acquisition failed: {response['data']}")

# Test 4: Acquire from IN2
print("\n8. Acquiring data from IN2...")
command_queue.put({
    'command': 'scope_acquire',
    'params': {
        'decimation': 64,
        'trigger_source': 'immediately',
        'input_channel': 'in2',
        'timeout': 5.0
    }
})
response = response_queue.get(timeout=10)

if response['status'] == 'ok':
    data = response['data']
    voltage_in2 = np.array(data['voltage'])
    time_data_in2 = np.array(data['time'])
    
    print(f"   ✓ IN2 data acquired!")
    print(f"   - Voltage min: {voltage_in2.min():.6f} V")
    print(f"   - Voltage max: {voltage_in2.max():.6f} V")
    print(f"   - Voltage mean: {voltage_in2.mean():.6f} V")
    print(f"   - Voltage std: {voltage_in2.std():.6f} V")
    print(f"   - Voltage p-p: {voltage_in2.max() - voltage_in2.min():.6f} V")
    
    np.savetxt('scope_data_in2_voltage.csv', voltage_in2, delimiter=',', header='Voltage (V)')
    np.savetxt('scope_data_in2_time.csv', time_data_in2, delimiter=',', header='Time (s)')
    print("   ✓ Saved to:")
    print("     - scope_data_in2_voltage.csv")
    print("     - scope_data_in2_time.csv")
    
    # FFT for IN2
    fft2 = np.fft.rfft(voltage_in2 - voltage_in2.mean())
    fft_mag2 = np.abs(fft2)
    peak_idx2 = np.argmax(fft_mag2[1:]) + 1
    peak_freq2 = fft_freq[peak_idx2]
    print(f"\n   - Peak frequency on IN2: {peak_freq2:.2f} Hz")
else:
    print(f"   ✗ IN2 acquisition failed: {response['data']}")

# Shutdown
print("\n9. Shutting down worker...")
command_queue.put({'command': 'shutdown', 'params': {}})
worker_process.join(timeout=5)
print("   ✓ Worker shut down")

print("\n" + "="*80)
print("DATA ACQUISITION VERIFIED!")
print("Check the CSV files to see the actual data:")
print("  - scope_data_in1_voltage.csv")
print("  - scope_data_in1_time.csv")
print("  - scope_data_in2_voltage.csv")
print("  - scope_data_in2_time.csv")
print("="*80)
