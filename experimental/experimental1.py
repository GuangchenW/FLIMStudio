import numpy as np
import phasorpy

from phasorpy.datasets import fetch
from phasorpy.io import signal_from_imspector_tiff, signal_from_ptu
from phasorpy.plot import plot_signal_image
from phasorpy.phasor import phasor_from_signal, phasor_to_signal, phasor_calibrate, phasor_filter_median, phasor_threshold
from phasorpy.plot import plot_phasor_image, plot_phasor

import matplotlib.pyplot as plt

image_path = "samples/Srijan.ptu"
ref_path = "samples/fluorescein2.ptu"

signal = signal_from_ptu(image_path, frame=-1, channel=0)
frequency = signal.attrs['frequency']
reference_signal = signal_from_ptu(ref_path, frame=-1, channel=1)
print(reference_signal.attrs['frequency'], frequency)
print(signal.shape, signal.dtype)

#plot_signal_image(signal, axis='H', xlabel='delay-time (ns)')

mean, real, imag = phasor_from_signal(signal, harmonic=1)

plot_phasor_image(mean, real, imag, title='Sample')


# Get phasor from image and reference
reference_mean, reference_real, reference_imag = phasor_from_signal(reference_signal, harmonic=1)
plot_phasor_image(reference_mean, reference_real, reference_imag, title='Sample')

# Calibration
real, imag = phasor_calibrate(
	real,
	imag,
	reference_mean,
	reference_real,
	reference_imag,
	frequency=frequency,
	lifetime=4.1,
)


# Median filter with size and repeat, just like FLUTE
mean, real, imag = phasor_filter_median(mean, real, imag, size=3, repeat=2)
# Intensity threshold
mean, real, imag = phasor_threshold(mean, real, imag, mean_min=0.05)

plot_phasor(
    real,
    imag,
    frequency=frequency,
    title='Calibrated, filtered phasor coordinates',
)