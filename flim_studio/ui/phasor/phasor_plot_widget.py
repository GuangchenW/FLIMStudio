from typing import Dict, Optional, List, TYPE_CHECKING
from dataclasses import dataclass

import numpy as np
from phasorpy.plot import PhasorPlot
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT

if TYPE_CHECKING:
	import napari

from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon, QColor
from qtpy.QtWidgets import (
	QWidget,
	QHBoxLayout,
	QVBoxLayout,
	QGroupBox,
	QFormLayout,
	QPushButton,
	QLineEdit,
	QLabel,
	QDoubleSpinBox,
	QListWidget,
	QListWidgetItem,
	QColorDialog,
)

class PhasorPlotWidget(QWidget):
	"""
	A QWidget for hosting a phasorpy PhasorPlot and the associated matplotlib axes.
	"""
	def __init__(
		self, 
		viewer:"napari.Viewer", 
		dpi:int = 120, 
		fig_pixels:int = 480, 
		parent:Optional[QWidget] = None
	) -> None:
		super().__init__(parent)
		self.viewer = viewer
		self.dpi = dpi
		self.fig_pixels = 480

		# --- Internal state --- #
		self._points:Dict[str, any] = {}

		self._build()

	## ------ UI ------ ##
	def _build(self) -> None:
		root = QVBoxLayout(self)
		root.setContentsMargins(5,5,5,5)

		# TODO: Plot controls
		ctrl_box = QGroupBox("Controls (coming soon)")
		ctrl_layout = QHBoxLayout(ctrl_box)
		root.addWidget(ctrl_box)

		# Phasor plot and roi management
		bottom = QHBoxLayout()
		root.addLayout(bottom, stretch=1) # We really care about the stretching factor here so safer to be explicit

		# Left: Matplotlib canvas for PhasorPlot
		left = QVBoxLayout()
		bottom.addLayout(left, stretch=1)

		fsize = self.fig_pixels/self.dpi
		self._fig = Figure(figsize=(fsize, fsize), dpi=self.dpi, tight_layout=True)
		self._canvas = FigureCanvasQTAgg(self._fig)
		self._toolbar = NavigationToolbar2QT(self._canvas, self)
		self._ax = self._fig.add_subplot(111)
		# Make PhasorPlot object and hand it control over the axes
		self._pp = PhasorPlot(ax=self._ax) # WARNING: Do we need the frequency argument here?
		self._pp.semicircle()

		left.addWidget(self._toolbar)
		left.addWidget(self._canvas, stretch=1)

		# Right: Cirlular ROI management panel
		right = QVBoxLayout()
		bottom.addLayout(right, stretch=0)

		# TODO: We need to think about how to arrange this ROI management panel.

	## ------ Public API ------ ##
	def add_points(self, name:str, g:np.ndarray, s:np.ndarray, **scatter_kwargs) -> None:
		""" Add or replace a named set of phasor points."""
		if name in self._points:
			try:
				for art in self._points[name]:
					art.remove()
			except Exception:
				pass
			self._points.pop(name, None)

		# Safeguard against infinite
		g = np.asarray(g).ravel()
		s = np.asarray(s).ravel()
		ok = np.isfinite(g) & np.isfinite(s)
		g,s = g[ok], s[ok]

		# NOTE: This returns list[matplotlib.lines.Line2D] which I need to figure out
		art_list = self._pp.hist2d(g,s)
		print(art_list)
		self._points[name] = art_list
		self._canvas.draw_idle()

	def remove_points(self, name:str, draw_now:bool=True) -> None:
		"""Remove a set of points by name."""
		art_list = self._points.pop(name, None)
		if not art_list is None:
			try:
				for art in art_list:
					art.remove()
			except Exception:
				pass
			if draw_now: self._canvas.draw_idle()

	def clear_points(self) -> None:
		"""Remove all point sets."""
		for name in self._points.keys():
			self.remove_points(name, False)
		self._canvas.draw_idle()