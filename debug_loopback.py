import time
import numpy as np

# Monkey-patch numpy to work around StemLab library's use of deprecated np.float
# This is necessary because StemLab has not been updated for modern numpy versions.
if not hasattr(np, "float"):
    np.float = np.float64
if not hasattr(np, "int"):
    np.int = np.int_
if not hasattr(np, "complex"):
    np.complex = np.complex128

from stemlab import StemLab
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Connection Parameters ---
# IMPORTANT: Please verify these are correct for your setup.
HOSTNAME = "100.107.106.75"
USER = "root"
PASSWORD = "root"

# --- Test Parameters ---
CHANNEL_OUT = "out2"
CHANNEL_IN = "in2"
VOLTAGE_TO_SET = 0.5
ACQUISITION_DURATION = 0.1  # seconds
DECIMATION = 64


def set_output_voltage(pyrpl, channel: str, voltage: float):
    """Sets the DC voltage of an analog output channel."""
    logging.info(f"Attempting to set {channel} to {voltage:.3f} V...")
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
    logging.info(f"ASG offset for {channel} is now: {asg.offset} V")
    logging.info(f"ASG amplitude for {channel} is now: {asg.amplitude} V")
    logging.info("Voltage set command sent.")


def acquire_trace(pyrpl, channel_in, decimation, duration):
    """Acquires a single trace from the oscilloscope."""
    logging.info(f"Configuring scope for {channel_in}...")
    scope = pyrpl.scope
    scope.input1 = channel_in
    scope.ch1_active = True
    scope.ch2_active = False
    scope.decimation = decimation
    scope.duration = max(duration, 0.11)
    scope.rolling_mode = True
    logging.info(
        f"Scope configured. Decimation={scope.decimation}, Duration={scope.duration:.3f}s, Rolling Mode={scope.rolling_mode}"
    )

    logging.info("Starting acquisition...")
    scope._start_acquisition_rolling_mode()
    wait_time = scope.duration + 0.1
    logging.info(f"Waiting {wait_time:.3f}s for data...")
    time.sleep(wait_time)

    times = scope.times
    data = scope._data_ch1
    logging.info(f"Acquisition complete. Acquired {len(data)} samples.")
    return times, data


def main():
    """Main function to run the loopback test."""
    pyrpl = None
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
        logging.info(f"Device IDN: StemLab on {pyrpl.parameters['hostname']}")

        # --- Run Test ---
        set_output_voltage(pyrpl, CHANNEL_OUT, VOLTAGE_TO_SET)
        times, data = acquire_trace(
            pyrpl, CHANNEL_IN, DECIMATION, ACQUISITION_DURATION
        )

        # --- Analyze Results ---
        if data is not None and len(data) > 0:
            mean_voltage = np.mean(data)
            logging.info(
                f"Mean voltage measured on {CHANNEL_IN}: {mean_voltage:.6f} V"
            )

            # Check if the result is close to the expected voltage
            if np.isclose(mean_voltage, VOLTAGE_TO_SET, atol=0.01):
                logging.info(
                    "SUCCESS: Measured voltage is close to the set voltage."
                )
            else:
                logging.error(
                    "FAILURE: Measured voltage is NOT close to the set voltage."
                )
                logging.error(
                    f"Expected: {VOLTAGE_TO_SET} V, Actual: {mean_voltage:.6f} V"
                )
        else:
            logging.error("FAILURE: No data was acquired.")

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
    finally:
        if pyrpl:
            logging.info("Disconnecting from Red Pitaya.")
            pyrpl.end()


if __name__ == "__main__":
    main()
