import numpy as np
import phasorpy

from phasorpy.datasets import fetch
from phasorpy.io import signal_from_imspector_tiff, signal_from_ptu
from phasorpy.phasor import phasor_from_signal
from phasorpy.lifetime import phasor_calibrate, phasor_to_lifetime_search
from phasorpy.plot import plot_phasor_image, plot_phasor

from flimlib import GCI_marquardt_fitting_engine

import matplotlib.pyplot as plt

image_path = "samples/NADH_12.ptu"
ref_path = "samples/Atto425_b_2.ptu"

reference_signal = signal_from_ptu(ref_path, frame=-1, channel=0)
signal = signal_from_ptu(image_path, frame=-1, channel=0)
frequency = signal.attrs['frequency']
print(reference_signal.attrs['frequency'], frequency)
print(signal.shape, signal.dtype)

mean, real, imag = phasor_from_signal(signal, harmonic=[1,2])
ref_mean, ref_real, ref_imag = phasor_from_signal(reference_signal)

c_real, c_imag = phasor_calibrate(
	real,
	imag,
	ref_mean,
	ref_real,
	ref_imag,
	frequency=frequency,
	lifetime=3.6
)

lifetime, fraction = phasor_to_lifetime_search(c_real, c_imag, frequency=frequency)
np.save("lifetime.npy", lifetime)
np.save("fraction.npy", fraction)