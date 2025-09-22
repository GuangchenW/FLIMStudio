from pathlib import Path
import numpy as np
from phasorpy.phasor import phasor_from_signal, phasor_center
from phasorpy.lifetime import phasor_from_lifetime, polar_from_reference_phasor

from .io import load_signal

class Calibration:
	def __init__(self) -> None:
		self.path: str|Path = "" # Path to reference
		self.signal = None # Reference signal
		self.ref_mean = None # Reference signal intensities
		self.ref_real = None # Reference signal real component (g)
		self.ref_imag = None # Reference signal imaginary component (s)

		self.phase_zero: float = 0.0 # phi calibration
		self.modulation_zero: float = 0.0 # m calibration

	def load(self, path:str|Path, channel:int=0) -> float|None:
		"""
		Load reference signals.
		"""
		self.signal = load_signal(path, channel)
		self.path = path

	def calibrate(self, frequency, lifetime):
		if self.signal is None:
			raise ValueError("Reference signal is None")
		# Compute phasor coordinates
		self.ref_mean, self.ref_real, self.ref_imag = phasor_from_signal(self.signal, axis='H')

		# NOTE: This thing is supposed to take numpy universal args, but doesn't take keepdims?
		self.phase_zero, self.modulation_zero = polar_from_reference_phasor(
			*phasor_center(
				self.ref_mean,
				self.ref_real,
				self.ref_imag,
			)[1:],
			*phasor_from_lifetime(
				frequency,
				lifetime,
			),
		)

	def get_signal_attribute(self, attr:str):
		"""
		Return the signal attribute (if exists) or None.
		"""
		return self.signal.attrs.get(attr, None)

	def get_calibration(self):
		"""
		Return the phase and modulation shift.
		For now, only handles the 2D case.
		"""
		return self.phase_zero, self.modulation_zero