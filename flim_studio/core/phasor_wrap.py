from __future__ import annotations
import numpy as np
from typing import Literal
import phasorpy as ppy

class PhasorError(Exception):
	pass

def phasor_from_signal(
	signal, # Expects xarray.DaatArray
	harmonic:int|Literal["all"] = 1,
	time_axis:str|int|None = "H",
):
	"""
	Wrapper function for phasor_from_signal from phasorpy.
	"""
	try:
		ph = ppy.phasor.phasor_from_signal(signal, axis=time_axis, harmonic=harmonic)
		return ph
	except Exception as e: # pragma: no cover - it depends entirely on the input signal
		raise PhasorError(str(e)) from e

def tau_map_from_gs(
	g_YX:np.adarray,
	s_YX:np.adarray,
	f_rep_hz:float,
) -> np.ndarray:
	"""
	Single-exp lifetime estimation: tau = s/(omega(1-g)).
	Returns tau in ns. 
	"""
	omega = 2 * np.pi * f_rep_hz
	denom = omega * (1.0-g_YX)
	tau_s = np.where(denom != 0, s_YX/denom, np.nan)
	tau_s[(g_YX<=0)|(g_YX>=1)] = np.nan
	tau_s[tau_s<0] = np.nan
	return tau_s*1e-9 # s -> ns