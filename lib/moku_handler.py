import time
from pathlib import Path

def setup_single_channel_logger(
    logger,
    channel=1,
    coupling="DC",
    impedance="1MOhm",
    voltage_range="10Vpp",
    acquisition_mode="Normal",
):
    """
    Set up one input channel on the Moku:Go Data Logger.

    Parameters
    ----------
    logger : Datalogger
        Moku Data Logger instrument handle.

    channel : int
        Input channel to enable and configure. Use 1 or 2.

    coupling : str
        Input coupling. Usually "DC" or "AC".

    impedance : str
        Input impedance. Usually "1MOhm" or "50Ohm", depending on the setup.

    voltage_range : str
        Input voltage range. "10Vpp" is a useful default for many basic labs.

    acquisition_mode : str
        Data Logger acquisition mode. "Normal" is a good default.
    """
    logger.enable_input(channel, enable=True)

    logger.set_frontend(
        channel=channel,
        impedance=impedance,
        coupling=coupling,
        range=voltage_range,
    )

    logger.set_acquisition_mode(mode=acquisition_mode)

def setup_two_channel_logger(
    logger,
    coupling="DC",
    impedance="1MOhm",
    voltage_range="10Vpp",
    acquisition_mode="Normal",
):
    """
    Set up both input channels on the Moku:Go Data Logger.

    This is just a convenience function that calls setup_single_channel_logger()
    once for Channel 1 and once for Channel 2.
    """
    setup_single_channel_logger(
        logger,
        channel=1,
        coupling=coupling,
        impedance=impedance,
        voltage_range=voltage_range,
        acquisition_mode=acquisition_mode,
    )

    setup_single_channel_logger(
        logger,
        channel=2,
        coupling=coupling,
        impedance=impedance,
        voltage_range=voltage_range,
        acquisition_mode=acquisition_mode,
    )

def log_data(
    logger,
    sampling_frequency,
    duration,
    filename_prefix="moku_go_data",
    save_directory="example_data",
    delay=0,
    use_trigger=False,
    trigger_source="Input1",
    trigger_level=0.1,
):
    """
    Record data using the Moku:Go Data Logger.

    The acquisition duration is calculated from the requested sampling frequency
    and number of samples:

        duration = number_of_samples / sampling_frequency

    This function saves the native Moku .li file on the computer. Conversion to
    CSV, NumPy, MATLAB, or HDF5 can be done later using mokucli.

    Parameters
    ----------
    logger : Datalogger
        Moku Data Logger instrument handle.

    sampling_frequency : float
        Sampling frequency in samples per second.

    duration : float
        Duration of the acquisition in seconds.

    filename_prefix : str
        Prefix for the saved .li file.

    save_directory : str
        Directory where the .li file will be saved. Default is "example_data".

    delay : float
        Delay before acquisition starts, in seconds. Default is 0.

    use_trigger : bool
        If False, acquisition begins after the delay.
        If True, acquisition waits for the selected input to cross the trigger level.

    trigger_source : str
        Trigger channel. For Moku:Go, use "Input1" or "Input2".

    trigger_level : float
        Trigger threshold in volts.

    Returns
    -------
    file_name : str
        Name of the saved .li file.
    """

    if use_trigger:
        result = logger.start_logging(
            duration=duration,
            sample_rate=sampling_frequency,
            file_name_prefix=filename_prefix,
            delay=delay,
            trigger_source=trigger_source,
            trigger_level=trigger_level,
        )
    else:
        result = logger.start_logging(
            duration=duration,
            sample_rate=sampling_frequency,
            file_name_prefix=filename_prefix,
            delay=delay,
        )

    print("Logging started.")

    while True:
        status = logger.logging_progress()

        if status["complete"]:
            break

        print(
            f"Samples logged: {status['samples_logged']}, "
            f"time remaining: {status['time_remaining']} s"
        )

        time.sleep(1)

    print("Logging complete.")

    # The file name is usually available from logging_progress().
    # If that fails for some reason, fall back to the start_logging() response.
    if "file_name" in status:
        file_name = status["file_name"]
    else:
        file_name = result["file_name"]

    cwd = Path.cwd()
    save_path = str(cwd / save_directory / file_name)

    logger.download(
        target="persist", 
        file_name=file_name,
        local_path=save_path
    )

    print(f"Saved to: {save_path}")

    return save_path