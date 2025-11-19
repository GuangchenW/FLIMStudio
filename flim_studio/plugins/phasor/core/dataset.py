import os
from pathlib import Path
from typing import TYPE_CHECKING
from dataclasses import dataclass, field

import numpy as np

from phasorpy.phasor import phasor_from_signal, phasor_filter_median
from phasorpy.lifetime import phasor_to_apparent_lifetime, phasor_to_normal_lifetime

from flim_studio.core.io import load_signal

if TYPE_CHECKING:
	import xarray

class Dataset:
	__slots__ = ("path", "name", "channel", "signal", "frequency", "counts", "mean",
		"real_raw", "imag_raw", "real_calibrated", "imag_calibrated", "g", "s",
		"phase_lifetime", "modulation_lifetime", "normal_lifetime", "max_count",
		"min_count", "kernel_size", "repetition", "mask", "group")

	def __init__(self, path:str|Path, channel:int):
		if not os.path.isfile(path):
			raise OSError(2, "No such file or directory", os.path.basename(path))
		# Essential data definition
		self.path: str|Path = path
		self.name: str = os.path.basename(path)
		self.channel: int = channel
		self.signal: "xarray.DataArray" = load_signal(path, channel)

		# Derived attributes
		self.counts: np.ndarray = self.photon_sum() # Sum of photon counts over H axis
		# Raw immutable phasor attributes
		self.mean, self.real_raw, self.imag_raw = phasor_from_signal(self.signal, axis='H')
		# Last seen frequency (MHz)
		self.frequency: float = self.signal.attrs.get("frequency", 80)
		self.frequency = self.frequency if self.frequency > 0 else 80
		# Calibrated phasors
		self.real_calibrated: np.ndarray = self.real_raw.copy()
		self.imag_calibrated: np.ndarray = self.imag_raw.copy()
		# Working data copy
		self.g: np.ndarray = self.real_calibrated.copy()
		self.s: np.ndarray = self.imag_calibrated.copy()
		# Compute apprent and normal lifetimes
		self.compute_lifetime_estimates()

		# Filter parameters
		self.min_count: int = 0
		self.max_count: int = 10000
		self.kernel_size: int = 3
		self.repetition: int = 0
		# Cached photon count thresholding mask
		self.mask = np.ones_like(self.mean, dtype=np.uint8)

		# Misc attributes
		self.group: str = "default"

	def calibrate_phasor(self, calibration:"Calibration") -> None:
		self.real_calibrated, self.imag_calibrated = calibration.compute_calibrated_phasor(self.real_raw, self.imag_raw)
		# Update working copy
		self.g = self.real_calibrated.copy()
		self.s = self.imag_calibrated.copy()
		# Update last seen frequency if calibration is provided
		if calibration and calibration.frequency > 0:
			self.frequency = calibration.frequency
		# Every time we re-calibrate, re-compute lifetime estimates
		self.compute_lifetime_estimates()

	def compute_lifetime_estimates(self) -> None:
		"""
		Compute and cache apparent and projected lifetime.
		"""
		self._compute_apparent_lifetime(self.frequency)
		self._compute_normal_lifetime(self.frequency)

	def reset_gs(self) -> None:
		"""
		Reset g and s to calibrated phasor.
		"""
		self.g = self.real_calibrated.copy()
		self.s = self.imag_calibrated.copy()

	def apply_median_filter(self) -> None:
		"""
		Apply median filter to g and s.
		"""
		if self.repetition < 1: return
		if self.kernel_size < 3: return
		# Mean is unchanged per documentation
		_, self.g, self.s = phasor_filter_median(self.mean, self.g, self.s, repeat=self.repetition, size=self.kernel_size)

	def apply_photon_threshold(self) -> None:
		"""
		Filter g and s based on total photon count of raw signal.
		Note that this turns the pixels outside the thresholds to nan.
		"""
		labels = self._photon_range_mask()
		self.mask = (labels == 1)
		# Set filtered pixels to 0, this is to maintain shape 
		self.g[~self.mask] = np.nan; self.s[~self.mask] = np.nan

	def photon_sum(self) -> np.ndarray:
		"""
		Sum raw signal over time-axis => photon counts per pixel.
		Returns (Y,X) uint32 np.ndarray.
		"""
		return self.signal.sum(dim='H').to_numpy()

	def summarize(self) -> dict:
		# TODO: Maybe find a way to standarize the property names
		out = {}
		out["name"] = self.name
		out["channel"] = self.channel
		out["group"] = self.group
		out["photon_count"] = self.counts.flatten()
		out["phi_lifetime"] = self.phase_lifetime.flatten()
		out["m_lifetime"] = self.modulation_lifetime.flatten()
		out["proj_lifetime"] = self.normal_lifetime.flatten()
		return out

	def display_name(self) -> str:
		return f"{self.name} (C{self.channel}) [{self.group}]"

	## ------ Internal ------ ##
	def _photon_range_mask(self) -> np.ndarray:
		"""
		Return a labels mask (Y,X) with values: 0=low, 1=kept, 2=high.
		"""
		low = self.counts < self.min_count
		high = self.counts > self.max_count
		kept = ~(low|high)

		labels = np.zeros_like(self.counts, dtype=np.uint8)
		labels[kept] = 1
		labels[high] = 2
		return labels

	def _compute_apparent_lifetime(self, frequency:float) -> None:
		self.phase_lifetime, self.modulation_lifetime = phasor_to_apparent_lifetime(self.g, self.s, frequency=self.frequency)

	def _compute_normal_lifetime(self, frequency:float) -> None:
		self.normal_lifetime = phasor_to_normal_lifetime(self.g, self.s, frequency=self.frequency)
