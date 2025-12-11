import numpy as np
import phasorpy

from phasorpy.datasets import fetch
from phasorpy.io import signal_from_imspector_tiff, signal_from_ptu
from phasorpy.plot import plot_signal_image
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

# signal["H"].diff("H").mean().item()
print("Before call", flush=True)
try:
	result = GCI_marquardt_fitting_engine(
		0.003999999984016789,
		[[[1,2,3,4,5,7,100,70,50,43,34,25,20,16,14,12,10,8,8]]],
		np.zeros((1,1,3), dtype=np.float32)
	)
	print("Call successful", flush=True)
except Exception as e:
	print("Call failed", flush=True)
print("Reached")
print(result is None)
print(result.param)