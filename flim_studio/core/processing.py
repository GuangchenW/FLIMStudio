import numpy as np
from typing import Tuple
from scipy.ndimage import median_filter

def photon_sum(signal_HYX:np.ndarray) -> np.ndarray:
	"""Sum over time-axis => photon counts per pixel.
	signal_HYX: (H,Y,X) uint array
	Returns (Y,X) uint32.
	"""
	if signal_HYX.ndim != 3:
		raise ValueError(f"Expected 3D (H,Y,X) instead got {signal_HYX.ndim}")
	return signal_HYX.sum(axis=0, dtype=np.uint32)

def photon_range_mask(
	photon_sum_YX:np.ndarray,
	min_photons:int = 0,
	max_photons:int|None = None,
) -> np.ndarray:
	"""
	Return a labels mask (Y,X) with values: 0=low, 1=kept, 2=high.
	"""
	if photon_sum_YX.ndim != 2:
		raise ValueError(f"Expected 2D (Y,X) photon sum, instead got {photon_sum_YX.ndim}")

	low = photon_sum_YX < min_photons
	high = np.zeros_like(low) if max_photons is None else photon_sum_YX > max_photons
	kept = ~(low|high)

	labels = np.zeros_like(photon_sum_YX, dtype=np.uint8)
	labels[kept] = 1
	labels[high] = 2
	return labels