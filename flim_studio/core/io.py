from __future__ import annotations
from pathlib import Path
from typing import Any
import phasorpy as ppy

def load_signal(path:str|Path) -> Any:
	"""Load a FLIM dataset via phasorpy IO.

	Returns a signal (xarray.DataArray) if successful.
	Rasies IOErrors on failure. 
	"""
	p = Path(path)
	if not p.exists():
		raise IOError(f"File not found: {p}")

	# Decide file loader based on file extension
	suffix = p.suffix.lower()
	try:
		if suffix in {".tif", ".tiff"}:
			try:
				sig = ppy.io.signal_from_imspector_tiff(str(p))
			except ValueError as e:
				print(".tiff/.tif files has to be of ImSpector origin due to metadata requirements.")
				raise
		elif suffix == ".ptu":
			sig = ppy.io.signal_from_ptu(str(p))
		else:
			raise IOError(f"Unsupported extensions: {suffix}")
		return sig
	except Exception as e:
		raise IOError(f"Failed to load {p}: {e}") from e