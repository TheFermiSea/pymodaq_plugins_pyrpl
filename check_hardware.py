import logging
logging.basicConfig(level=logging.DEBUG)

from stemlab import StemLab

config = {
    'hostname': '100.107.106.75',
    'user': 'root',
    'password': 'root',
}

try:
    print("Attempting to connect to the Red Pitaya with debug logging...")
    stemlab = StemLab(**config)
    print("Successfully connected to the Red Pitaya!")
    stemlab.end()
    print("Connection closed.")
except Exception as e:
    print(f"Failed to connect to the Red Pitaya: {e}")