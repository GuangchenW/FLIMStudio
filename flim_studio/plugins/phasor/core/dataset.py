from pathlib import Path
from typing import TYPE_CHECKING
from dataclasses import dataclass, field

import numpy as np

from phasorpy.phasor import phasor_from_signal, phasor_filter_median
from phasorpy.lifetime import phasor_to_apparent_lifetime, phasor_to_normal_lifetime

if TYPE_CHECKING:
	import xarray

@dataclass
class Dataset:
	# TODO: We really need to think hard about this data model.
	# I think it's going to be too bloated.
	path: str|Path
	name: str
	channel: int
	signal: "xarray.DataArray"
	frequency: float = field(init=False) # Last used frequency
	total: np.ndarray = field(init=False) # Sum of photons over H axis
	mean: np.ndarray = field(init=False) # Mean signal
	real_raw: np.ndarray = field(init=False) # Raw real phasor
	imag_raw: np.ndarray = field(init=False) # Raw imaginary phasor
	real_calibrated: np.ndarray = field(init=False) # Calibrated real phasor
	imag_calibrated: np.ndarray = field(init=False) # Calibrated imaginary phasor
	g: np.ndarray = field(init=False) # Processed real coords, exactly as in graph
	s: np.ndarray = field(init=False) # Processed imaginary coords, exactly as in graph
	phase_lifetime: np.ndarray = field(init=False) # Apparent phase lifetime
	modulation_lifetime: np.ndarray = field(init=False) # Apparent modulation lifetime
	normal_lifetime: np.ndarray = field(init=False) # Projected lifetime

	def __post_init__(self) -> None:
		self.total = self.photon_sum()
		self.compute_phasor()
		# Calibrate without calibration to init other properties
		self.calibrate_phasor()

	def compute_phasor(self) -> None:
		"""
		Compute mean, real and imag, then sync all downstream properties.
		"""
		self.mean, self.real_raw, self.imag_raw = phasor_from_signal(self.signal, axis='H')
		self.frequency = self.signal.attrs.get("frequency", 0)

	def calibrate_phasor(self, calibration:"Calibration"=None) -> None:
		if calibration:
			self.real_calibrated, self.imag_calibrated = calibration.compute_calibrated_phasor(self.real_raw, self.imag_raw)
		else:
			self.real_calibrated = self.real_raw
			self.imag_calibrated = self.imag_raw
		self.g = self.real_calibrated
		self.s = self.imag_calibrated
		# Every time we re-calibrate, re-compute lifetime estimates
		if calibration and calibration.frequency > 0:
			self.frequency = calibration.frequency
		self.compute_lifetime_estimates()

	def compute_lifetime_estimates(self) -> None:
		"""
		Compute and cache apparent and projected lifetime.
		"""
		frequency = self.frequency if self.frequency > 0 else 80
		self._compute_apparent_lifetime(frequency)
		self._compute_normal_lifetime(frequency)

	def reset_gs(self) -> None:
		"""
		Reset g and s to calibrated phasor.
		"""
		self.g = self.real_calibrated.copy()
		self.s = self.imag_calibrated.copy()

	def apply_median_filter(self, kernel_size:int=3, repetition:int=0) -> None:
		"""
		Apply median filter to g and s.
		"""
		if repetition < 1: return
		if kernel_size < 3: return
		# Mean is unchanged per documentation
		_, self.g, self.s = phasor_filter_median(self.mean, self.g, self.s, repeat=repetition, size=kernel_size)

	def apply_photon_threshold(self, min_thresh:int=0, max_thresh:int|None=None) -> None:
		"""
		Filter g and s based on total photon count of raw signal.
		Note that this turns the pixels outside the thresholds to nan.
		"""
		labels = self._photon_range_mask(self.photon_sum(), min_thresh, max_thresh)
		mask = (labels == 1)
		# Set filtered pixels to 0, this is to maintain shape 
		self.g[~mask] = np.nan; self.s[~mask] = np.nan

	def photon_sum(self) -> np.ndarray:
		"""
		Sum raw signal over time-axis => photon counts per pixel.
		Returns (Y,X) uint32 np.ndarray.
		"""
		return self.signal.sum(dim='H')

	## ------ Internal ------ ##
	def _photon_range_mask(
		self,
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

	def _compute_apparent_lifetime(self, frequency:float) -> None:
		self.phase_lifetime, self.modulation_lifetime = phasor_to_apparent_lifetime(self.g, self.s, frequency=frequency)

	def _compute_normal_lifetime(self, frequency:float) -> None:
		self.normal_lifetime = phasor_to_normal_lifetime(self.g, self.s, frequency=frequency)
