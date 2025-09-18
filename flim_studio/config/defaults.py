from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Defaults:
	## --- Plotting --- ##
	# Peformance
	max_phasor_points : int = 200_000
	# Filtering
	photon_min_default : int = 0
	photon_max_default : int | None = None # None => unlimited
	median_kernel_default : int = 1 # Has to be positive odd integer