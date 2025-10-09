from pathlib import Path
from typing import TYPE_CHECKING
from dataclasses import dataclass, field

import numpy as np

from phasorpy.phasor import phasor_from_signal
from phasorpy.lifetime import phasor_to_apparent_lifetime, phasor_to_normal_lifetime

if TYPE_CHECKING:
	import xarray

@dataclass
class Dataset:
	path: str|Path
	name: str
	channel: int
	signal: "xarray.DataArray"
	frequency: float = field(init=False) # Last used frequency
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

	def compute_phasor(self) -> None:
		"""
		Compute mean, real and imag, then sync all downstream properties.
		"""
		self.mean, self.real_raw, self.imag_raw = phasor_from_signal(self.signal, axis='H')
		self.frequency = self.signal.attrs.get("frequency", 0)
		# Calibrate without calibration to init other properties
		self.calibrate_phasor()

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

	def _compute_apparent_lifetime(self, frequency:float) -> None:
		self.phase_lifetime, self.modulation_lifetime = phasor_to_apparent_lifetime(self.g, self.s, frequency=frequency)

	def _compute_normal_lifetime(self, frequency:float) -> None:
		self.normal_lifetime = phasor_to_normal_lifetime(self.g, self.s, frequency=frequency)
