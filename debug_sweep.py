import time
import numpy as np
from stemlab import StemLab
import logging

# Monkey-patch numpy to work around StemLab library's use of deprecated np.float
if not hasattr(np, "float"):
    np.float = np.float64
if not hasattr(np, "int"):
    np.int = np.int_
if not hasattr(np, "complex"):
    np.complex = np.complex128

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Connection Parameters ---
HONAME = "100.107.106.75"
USER = "root"
PASSWORD = "root"

# --- Test Parameters ---
CHANNEL_OUT = "out2"
CHANNEL_IN = "in2"
ACQUISITION_DURATION = 0.1  # seconds
DECIMATION = 64


def set_output_voltage(pyrpl, channel: str, voltage: float):
    """Sets the DC voltage of an analog output channel."""
    if channel == "out1":
        asg = pyrpl.asg0
    else:
        asg = pyrpl.asg1

    asg.setup(
        waveform="dc",
        amplitude=voltage,
        offset=voltage,
        output_direct=channel,
        trigger_source="immediately",
    )
    time.sleep(0.1)  # Allow hardware to settle


def acquire_trace(pyrpl, channel_in, decimation, duration):
    """Acquires a single trace from the oscilloscope."""
    scope = pyrpl.scope
    scope.input1 = channel_in
    scope.ch1_active = True
    scope.ch2_active = False
    scope.decimation = decimation
    scope.duration = max(duration, 0.11)
    scope.rolling_mode = True

    scope._start_acquisition_rolling_mode()
    wait_time = scope.duration + 0.1
    time.sleep(wait_time)

    data = scope._data_ch1
    return data


def main():
    """Main function to run the voltage sweep test."""
    pyrpl = None
    results = []
    try:
        # --- Connect ---
        logging.info(f"Connecting to Red Pitaya at {HOSTNAME}...")
        config = {
            "hostname": HOSTNAME,
            "user": USER,
            "password": PASSWORD,
            "reloadfpga": False,
            "autostart": True,
            "timeout": 10,
        }
        pyrpl = StemLab(**config)
        logging.info("Successfully connected.")

        # --- Define the sweep voltages ---
        sweep_voltages = np.linspace(
            -1.0, 1.0, 21
        )  # from -1.0V to 1.0V in 0.1V steps

        print("\n--- Starting Voltage Sweep ---")
        print("Set Voltage (V) | Measured Voltage (V)")
        print("----------------|--------------------")

        # --- Run Sweep ---
        for voltage in sweep_voltages:
            set_output_voltage(pyrpl, CHANNEL_OUT, voltage)
            data = acquire_trace(
                pyrpl, CHANNEL_IN, DECIMATION, ACQUISITION_DURATION
            )

            if data is not None and len(data) > 0:
                mean_voltage = np.mean(data)
                print(f"{voltage:^15.3f} | {mean_voltage:^20.6f}")
                results.append((voltage, mean_voltage))
            else:
                print(f"{voltage:^15.3f} | {'NO DATA':^20}")
                results.append((voltage, None))

        print("--- Voltage Sweep Complete ---\n")

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
    finally:
        if pyrpl:
            logging.info("Disconnecting from Red Pitaya.")
            pyrpl.end()


if __name__ == "__main__":
    main()
