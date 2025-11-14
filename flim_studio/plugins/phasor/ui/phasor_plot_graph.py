from typing import Optional, Literal, TYPE_CHECKING

from qtpy.QtCore import Signal
from qtpy.QtWidgets import QWidget, QVBoxLayout

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT

from phasorpy.plot import PhasorPlot

from flim_studio.core.widgets import MPLGraph

if TYPE_CHECKING:
	from ..core import Dataset
	from matplotlib.axes import Axes

class PhasorGraphWidget(MPLGraph):
	"""
	QWidget container for matplotlib figure and phasor plot related APIs.
	"""
	def __init__(
		self,
		frequency: float|None = None,
		dpi: int = 120,
		fig_pixels: int = 480,
		parent: QWidget|None = None
	) -> None:
		super().__init__(dpi=dpi, fig_pixels=fig_pixels, parent=parent)
		self.frequency = frequency
		self._pp = PhasorPlot(ax=self.get_ax(), frequency=self.frequency)
		self.draw_idle()

	## ------ Public API ------ ##
	def clear_plot(self) -> None:
		"""
		Reset the plot.
		"""
		# This is nasty, but I don't think there is a more reliable way?
		xlim = self._ax.get_xlim()
		ylim = self._ax.get_ylim()
		xscale = self._ax.get_xscale()
		yscale = self._ax.get_yscale()
		aspect = self._ax.get_aspect()
		# HACK: Save the circle ROI patches before clearing and add back.
		# This works, but not scalable once we add arrows, component analysis, etc.
		patches = self._ax.patches[:]
		self._ax.cla()
		for p in patches:
			self._ax.add_patch(p)
		self._ax.set_xlim(xlim)
		self._ax.set_ylim(ylim)
		self._ax.set_xscale(xscale)
		self._ax.set_yscale(yscale)
		self._ax.set_aspect(aspect)

		if self.frequency:
			self._ax.set_title(f"Phasor plot ({self.frequency} MHz)")
		else:
			self._ax.set_title("Phasor plot")
		self._ax.set_xlabel("G, real")
		self._ax.set_ylabel("S, imag")
		self._draw_semicircle()

	def draw_dataset(
		self,
		dataset: "Dataset",
		min_photon_count: int = 0,
		max_photon_count: int = int(1e9),
		median_filter_size: int = 3,
		median_filter_repetition: int = 0,
		mode:Literal["scatter","hist2d","contour"] = "contour",
		cmap:str = "jet",
	) -> None:
		"""
		Plot the given dataset.
		:param min_photon_count: Minimum photon count for a pixel to be plotted. Default 0.
		:param max_photon_count: Maximum photon count for a pixel to be plotted. Deafult 1e9.
		:param median_filter_size: Median filter kernel size (nxn). Default 3.
		:param median_filter_repetition: Number of times median filter is applied. 
			If <1, no filter is applied. Default 0.
		:param mode: Plotting mode. Accepts plot, hist2d, contour. Default contour.
		:param color: Plot color. 
		"""
		dataset.reset_gs()
		dataset.apply_median_filter(median_filter_size, median_filter_repetition)
		dataset.apply_photon_threshold(min_photon_count, max_photon_count)
		dataset.compute_lifetime_estimates()
		# Slice only meaningful values for efficient plotting
		# HACK: A little hacky, probably should let Dataset do this
		g = dataset.g; s = dataset.s
		g = g[~np.isnan(g)]
		s = s[~np.isnan(s)]
		match mode:
			case "scatter":
				self._pp.plot(g, s, fmt='.')
			case "hist2d":
				self._pp.hist2d(g, s, cmap=cmap)
			case "contour":
				self._pp.contour(g, s, cmap=cmap)

	## ------ Internal ------ ##
	def _draw_semicircle(self) -> None:
		# We have to give it frequency here because apparently PhasorPlot does not
		# keep track of the frequency value given in init.
		self._pp.semicircle(frequency=self.frequency, lifetime=[0.5,1,2,4,8])