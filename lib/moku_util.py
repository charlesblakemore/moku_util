import subprocess
import numpy as np
from scipy import signal

import matplotlib.pyplot as plt
plt.rcParams.update({
    'font.size': 14,
})

from moku_handler import *


class DataFile:
    """Container and utility methods for Moku-exported time-series data.

    Attributes
    ----------
    data : np.ndarray | None
        Stacked input channels with shape (n_channels, n_samples).
        
    time : np.ndarray | None
        Time axis in seconds.

    nsamp : int | None
        Number of samples in each channel.

    fsamp : float | None
        Sampling frequency in Hz.

    filename : str | None
        Path to the currently loaded data file.

    peaks : list[np.ndarray | None]
        Per-channel peak sample indices. Index 0 => channel 1, index 1 => channel 2.

    peak_properties : list[dict | None]
        Per-channel peak property dicts returned by ``scipy.signal.find_peaks``.

    peak_start_indices : list[np.ndarray | None]
        Per-channel left-base sample indices for each detected peak.

    peak_end_indices : list[np.ndarray | None]
        Per-channel right-base sample indices for each detected peak.

    peak_durations : list[np.ndarray | None]
        Per-channel duration (s) of each detected peak.

    peak_integrals : list[np.ndarray | None]
        Per-channel integrated area for each detected peak.

    peak_noise_mean : list[float | None]
        Per-channel mean background level estimated outside peak windows.

    peak_pre_samples : int | None
        Number of samples before each peak used for integration.

    peak_post_samples : int | None
        Number of samples after each peak used for integration.
    """

    def __init__(self, filename=None, verbose=True):
        """Initialize the data container and optionally load a file.
        Relevant class attributes, metadata, and actual data are 
        initialized to "None" until a file is loaded.

        Parameters
        ----------
        filename : str | None, optional
            Path to a supported data file (.npy or .li), by default None.

        verbose : bool, optional
            If True, print status and warning messages, by default True.
        """
        # Core attributes related to the raw data
        self.data = None
        self.time = None
        self.nsamp = None
        self.fsamp = None
        self.filename = filename

        # Attributes below are related to data with transient events (i.e. peaks)
        # and are populated by various class methods that analyze the data
        # Per-channel lists; index 0 => channel 1, index 1 => channel 2.
        self.peaks = [None, None]
        self.peak_properties = [None, None]
        self.peak_start_indices = [None, None]
        self.peak_end_indices = [None, None]
        self.peak_durations = [None, None]
        self.peak_integrals = [None, None]
        self.peak_noise_mean = [None, None]

        # Symmetric pre/post sample counts for both channels
        self.peak_pre_samples = None
        self.peak_post_samples = None

        if self.filename is not None:
            self.load_data(self.filename, verbose=verbose)


    def load_data(
            self, 
            filename, 
            verbose=True
        ):
        """Load waveform data from disk.

        If a `.li` file is provided, it is converted to `.npy` format with
        `mokucli` (unless a converted file already exists).

        Parameters
        ----------
        filename : str
            Path to the source data file.

        verbose : bool, optional
            If True, print status and warning messages, by default True.
        """

        # Split the filename into root and extension to check for .li format.
        filepath = Path(filename)
        if filepath.suffix == '.li':
            npyFilename = filepath.with_suffix('.npy')

            # Only convert if the .npy file doesn't already exist.
            if not Path(npyFilename).is_file():
                if verbose:
                    print(f"Converting file: <{filename}> to .npy format.")

                # Use the mokucli CLI tool to convert the .li file to .npy.
                subprocess.run(["mokucli", "convert", filename, "--format", "npy"])
            else:
                if verbose:
                    print(f"Using existing .npy file: <{npyFilename}>")

            # Point filename to the converted .npy file for subsequent loading.
            filename = npyFilename

        # Store the filename in the class attribute for reference.
        self.filename = filename

        # Try to load the raw data
        try:
            rawData = np.load(filename, allow_pickle=True)
        except Exception as e:
            print(f"Error loading raw data: {e}")

        # Core metadata derived from the time axis.
        self.time = rawData['Time (s)']
        self.nsamp = len(self.time)

        # Assuming uniform sampling, calculate fsamp from the spacing of
        # the first two samples
        self.fsamp = 1.0 / (self.time[1] - self.time[0])

        # Try loading the two inputs, but allow for the possibility that one 
        # may be missing depending on how the user acquired/exported the data.
        input1 = None
        try:
            input1 = rawData['Input 1 (V)']
        except ValueError:
            if verbose:
                print("Warning: 'Input 1 (V)' not found in raw data. Using 'Input 2 (V)' only.")

        input2 = None
        try:
            input2 = rawData['Input 2 (V)']
        except ValueError:
            if verbose:
                print("Warning: 'Input 2 (V)' not found in raw data. Using 'Input 1 (V)' only.")
        
        # Keep a consistent (n_channels, n_samples) shape, regardless of how
        # many channels were successfully loaded.
        if input1 is None:
            self.data = np.stack((input2,), axis=0)
        elif input2 is None:
            self.data = np.stack((input1,), axis=0)
        else:
            self.data = np.stack((input1, input2), axis=0)
        
    def plot_data(
            self, 
            input=None, 
            microseconds=False, 
            show=True, 
            figsize=(8,5), 
            xlim=None, 
            ylim=None, 
            legend_fontsize=10
        ):
        """Plot one or more loaded input channels.

        Parameters
        ----------
        input : list[int] | None, optional
            Channel indices to plot (0-based). If None, plots all available
            channels.

        microseconds : bool, optional
            If True, plot time in microseconds; otherwise seconds.

        show : bool, optional
            If True, display the figure immediately.

        figsize : tuple[float, float], optional
            Matplotlib figure size.

        xlim : tuple[float, float] | None, optional
            X-axis limits in the displayed time units.

        ylim : tuple[float, float] | None, optional
            Y-axis limits.

        Returns
        -------
        tuple
            (fig, ax) Matplotlib figure and axis objects.
        """
        
        # Default to plotting all available channels if none are specified.
        if input is None:
            if self.data.size == self.nsamp:
                input = [0]
            else:
                input = [0, 1]

        # Create the figure and axis with the specified size.
        fig, ax = plt.subplots(figsize=figsize)

        # Copy the time array to avoid modifying the original data.
        xplot = np.copy(self.time)

        # Scale time to microseconds if requested, and label the axis accordingly.
        if microseconds:
            xplot *= 1e6
            ax.set_xlabel(r'Time ($\mu$s)')
        else:
            ax.set_xlabel('Time (s)')

        # Build a boolean mask for the x limits to avoid plotting
        # unnecessary data to reduce RAM consumption.
        if xlim is not None:
            mask = (xplot >= xlim[0]) * (xplot <= xlim[1])
        else:
            mask = np.ones_like(xplot, dtype=bool)

        # Plot each requested channel, using the mask to restrict the x range.
        for i in input:
            ax.plot(xplot[mask], self.data[i][mask], label=f'Input {i+1}')
        ax.set_ylabel('Voltage (V)')

        # Apply axis limits if provided. If the axis limits are not explicitly
        # specified, the plot will include some whitespace gaps to either side 
        # of the data, even after the mask is applied.
        if xlim is not None:
            ax.set_xlim(xlim)
        if ylim is not None:
            ax.set_ylim(ylim)

        # Build the legend and apply tight layout to minimize whitespace.
        ax.legend(fontsize=legend_fontsize)
        fig.tight_layout()

        # Display the figure immediately if requested.
        if show:
            plt.show()

        return fig, ax
    



    def find_peaks(
            self, 
            channel=0, 
            height=0.5, 
            width=1, 
            prominence=(0.3, None),
            negative_signal=False
        ):
        """Find peaks in the specified input channel and store peak metadata.

        Parameters
        ----------
        channel : int, optional
            Channel index (0-based) to analyze, by default 0.

        height : float | tuple[float, float] | None, optional
            Minimum peak height passed to `scipy.signal.find_peaks`.

        width : float | tuple[float, float] | None, optional
            Minimum peak width passed to `scipy.signal.find_peaks`.

        prominence : tuple[float | None, float | None] | float | None, optional
            Peak prominence requirement passed to `scipy.signal.find_peaks`.
            First number is minimum prominence, second number is maximum prominence.

        negative_signal : bool, optional
            If True, look for negative peaks instead of positive peaks. All other
            parameters should still be specified as positive values, but correspond
            to negative peak heights and prominences under the hood.
        """
        if self.data is None or self.time is None:
            raise ValueError("No data loaded. Use load_data() before finding peaks.")
        if channel >= self.data.shape[0]:
            raise ValueError(f"Channel {channel} not available. Data has {self.data.shape[0]} channel(s).")

        # Run SciPy peak finding on the specified channel and retain the
        # returned property dictionary so downstream analysis can reuse it.
        fac = -1 if negative_signal else 1
        peaks, peak_properties = signal.find_peaks(
            self.data[channel] * fac,
            height=height,
            width=width,
            prominence=prominence
        )
        self.peaks[channel] = peaks
        self.peak_properties[channel] = peak_properties

        # Convert the peak base locations into valid integer sample indices.
        # These bases provide a physically meaningful start/end estimate for
        # each detected peak and are reused by later plotting/integration code.
        left_bases = np.clip(
            np.asarray(peak_properties['left_bases'], dtype=int),
            0,
            self.nsamp - 1
        )
        right_bases = np.clip(
            np.asarray(peak_properties['right_bases'], dtype=int),
            0,
            self.nsamp - 1
        )

        # Store the peak extents and compute a duration in seconds for each
        # detected event from the corresponding time-axis samples.
        self.peak_start_indices[channel] = left_bases
        self.peak_end_indices[channel] = right_bases
        self.peak_durations[channel] = (
            self.time[right_bases] - self.time[left_bases]
        )

    def _get_peak_integration_bounds(self, channel=0):
        """Return per-peak integration bounds derived from stored settings.

        Parameters
        ----------
        channel : int, optional
            Channel index (0-based) to compute bounds for, by default 0.
        """
        if self.peaks[channel] is None:
            raise ValueError(f"No peaks found for channel {channel}. Use find_peaks() before requesting integration bounds.")
        if self.peak_pre_samples is None or self.peak_post_samples is None:
            raise ValueError("No integration settings found. Use integrate_peaks() first.")

        # Derive the integration bounds on demand instead of storing separate
        # start/end arrays that can always be reconstructed from peak indices
        # and the configured numbers of pre/post samples.
        start_indices = np.clip(
            self.peaks[channel] - self.peak_pre_samples,
            0,
            self.nsamp
        )
        end_indices = np.clip(
            self.peaks[channel] + self.peak_post_samples,
            0,
            self.nsamp
        )

        return start_indices, end_indices


    def integrate_peaks(
            self, 
            channel=0, 
            pre_peak=2, 
            post_peak=5,
            baseline=None
        ):
        """Integrate previously identified peaks in the specified input channel.

        Peak integrals and supporting metadata are stored as class attributes.

        Parameters
        ----------
        channel : int, optional
            Channel index (0-based) to integrate, by default 0.

        pre_peak : int, optional
            Number of samples to include before each peak index.

        post_peak : int, optional
            Number of samples to include after each peak index.
        """
        # Require previously identified peaks before attempting integration.
        if self.peaks[channel] is None or self.peak_properties[channel] is None:
            raise ValueError(f"No peaks found for channel {channel}. Use find_peaks() before integrating peaks.")

        # Store only the integration window configuration. The actual per-peak
        # sample bounds can be reconstructed later from these values and the
        # saved peak locations, so separate start/end arrays are unnecessary.
        self.peak_pre_samples = pre_peak
        self.peak_post_samples = post_peak

        # Start with all samples marked as noise, then remove integration windows.
        integrals = []
        noise_mask = np.ones_like(self.data[channel], dtype=bool)
        integration_start_indices, integration_end_indices = self._get_peak_integration_bounds(channel=channel)

        # Integrate each stored peak over its corresponding sample window.
        for left, right in zip(
            integration_start_indices,
            integration_end_indices
        ):
            # Exclude the integration window from the noise estimate.
            left = int(left)
            right = int(right)

            noise_mask[left:right] = False
            integrals.append(np.sum(self.data[channel][left:right]))

        # Store the computed integrals so they can be analyzed later.
        self.peak_integrals[channel] = np.array(integrals)

        # Estimate the mean background level from samples outside all peak windows.
        if baseline is None:
            if np.any(noise_mask):
                baseline = np.mean(self.data[channel][noise_mask])
            else:
                baseline = np.nan

        self.peak_noise_mean[channel] = baseline


    def plot_peak_integrations(
            self, 
            channel=0, 
            plot_grid=(3,3), 
            nplot=1, 
            plot_buffer=10
        ):
        """Plot randomly selected integrated peak windows for the given channel.

        Parameters
        ----------
        channel : int, optional
            Channel index (0 or 1) to plot, by default 0.

        plot_grid : tuple[int, int], optional
            Subplot grid shape for each figure.

        nplot : int, optional
            Number of figures to generate.

        plot_buffer : int, optional
            Additional samples to show on either side of the integration window.
        """
        # Require both detected peaks and previously computed integration windows.
        if self.peaks[channel] is None or len(self.peaks[channel]) == 0:
            raise ValueError("No peaks found. Use find_peaks() before plotting peak integrations.")
        if self.peak_pre_samples is None or self.peak_post_samples is None:
            raise ValueError("No integrated peaks found. Use integrate_peaks() before plotting.")

        # Reconstruct the integration bounds from the stored configuration so
        # plotting stays consistent with the earlier integration step.
        integration_start_indices, integration_end_indices = self._get_peak_integration_bounds(channel=channel)

        # Randomly sample from the stored peaks so each panel shows one example.
        rng = np.random.default_rng()
        for _ in range(nplot):
            # Build a shared-axis grid to make visual comparison easier.
            fig, ax = plt.subplots(
                plot_grid[0], plot_grid[1],
                figsize=(2*plot_grid[1]+0.25, 2*plot_grid[0]+0.25),
                sharex='all', sharey='all'
            )

            # Force a 2D axes array so the indexing works for any grid shape.
            ax = np.atleast_2d(ax)
            for j in range(plot_grid[0] * plot_grid[1]):
                # Convert the flat panel index into row/column coordinates.
                row = j // plot_grid[1]
                col = j % plot_grid[1]

                # Choose one previously integrated peak to display.
                peak_idx = rng.integers(len(self.peaks[channel]))
                peak = self.peaks[channel][peak_idx]
                fill_left = int(integration_start_indices[peak_idx])
                fill_right = int(integration_end_indices[peak_idx])

                # Expand the view window beyond the integration region for context.
                plot_left = max(0, fill_left - plot_buffer)
                plot_right = min(self.nsamp, fill_right + plot_buffer)

                # Plot the local waveform centered on the peak time.
                ax[row, col].plot(
                    1e6 * (self.time[plot_left:plot_right] - self.time[peak]),
                    self.data[channel][plot_left:plot_right],
                    color='C0'
                )

                # Shade the exact region that was used in the stored integral.
                ax[row, col].fill_between(
                    1e6 * (self.time[fill_left:fill_right] - self.time[peak]),
                    self.data[channel][fill_left:fill_right],
                    self.peak_noise_mean[channel],
                    color='C0', alpha=0.5
                )

                # Draw reference lines for the estimated noise floor and peak center.
                ax[row, col].axhline(self.peak_noise_mean[channel], color='red', linestyle='--')
                ax[row, col].axvline(0, color='C1', linestyle='--')

                # Label only the outer axes to keep the grid uncluttered.
                if row == plot_grid[0] - 1:
                    ax[row, col].set_xlabel(r'Time ($\mu$s)')
                if col == 0:
                    ax[row, col].set_ylabel('Amplitude (V)')

            # Tighten spacing before displaying the finished figure.
            plt.tight_layout()
            plt.show()


