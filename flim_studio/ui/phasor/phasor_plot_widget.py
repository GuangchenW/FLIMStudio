from typing import Dict, Optional, List, Literal, TYPE_CHECKING
from dataclasses import dataclass

import numpy as np
from phasorpy.plot import PhasorPlot
from phasorpy.phasor import phasor_filter_median
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT

if TYPE_CHECKING:
	import napari
	from .sample_manager_widget import Dataset
from flim_studio.core.processing import photon_range_mask

from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon, QColor
from qtpy.QtWidgets import (
	QWidget,
	QHBoxLayout,
	QVBoxLayout,
	QGridLayout,
	QGroupBox,
	QFormLayout,
	QPushButton,
	QLineEdit,
	QLabel,
	QSpinBox,
	QDoubleSpinBox,
	QListWidget,
	QListWidgetItem,
	QComboBox,
	QColorDialog,
)

class PhasorPlotWidget(QWidget):
	"""
	A QWidget for hosting a phasorpy PhasorPlot and the associated matplotlib figure.
	"""
	def __init__(
		self, 
		viewer: "napari.Viewer",
		datasets: List["Dataset"],
		dpi: int = 120, 
		fig_pixels: int = 480,
		frequency: float|None = None,
		parent: QWidget|None = None,
	) -> None:
		super().__init__(parent)
		self.viewer = viewer
		self.dpi = dpi
		self.fig_pixels = fig_pixels
		self.frequency: float|None = frequency

		# --- Internal state --- #
		self._points:Dict[str, any] = {}
		self._datasets = datasets

		self._build()

	## ------ UI ------ ##
	def _build(self) -> None:
		root = QVBoxLayout(self)
		root.setContentsMargins(5,5,5,5)

		# --- Plot controls --- #
		ctrl_box = QGroupBox("Controls")
		ctrl_grid = QGridLayout()
		ctrl_grid.setContentsMargins(5,15,5,5)
		ctrl_box.setLayout(ctrl_grid)
		root.addWidget(ctrl_box)
		#  --- Left side: filter control
		# First row: intensity filter
		min_count_label = QLabel("Min photon count")
		max_count_label = QLabel("Max photon count")
		self.min_count = QSpinBox()
		self.min_count.setRange(0, int(1e9))
		self.max_count = QSpinBox()
		self.max_count.setRange(1, int(1e9))
		self.max_count.setValue(int(1e9))
		ctrl_grid.addWidget(min_count_label, 1, 1)
		ctrl_grid.addWidget(self.min_count, 1, 2)
		ctrl_grid.addWidget(max_count_label, 1, 3)
		ctrl_grid.addWidget(self.max_count, 1, 4)
		# Second row: median filter
		kernel_size_label = QLabel("Median filter size")
		repetition_label = QLabel("Median filter repetition")
		self.kernel_size = QSpinBox()
		self.kernel_size.setRange(1, 99)
		self.kernel_size.setValue(3)
		self.repetition = QSpinBox()
		self.repetition.setRange(0, 99)
		ctrl_grid.addWidget(kernel_size_label, 2, 1)
		ctrl_grid.addWidget(self.kernel_size, 2, 2)
		ctrl_grid.addWidget(repetition_label, 2, 3)
		ctrl_grid.addWidget(self.repetition, 2, 4)
		# Third row: plot mode and parameters
		mode_label = QLabel("Plot mode")
		self.mode_combo_box = QComboBox()
		self.mode_combo_box.addItem("contour")
		self.mode_combo_box.addItem("scatter")
		self.mode_combo_box.addItem("hist2d")
		ctrl_grid.addWidget(mode_label, 3, 1)
		ctrl_grid.addWidget(self.mode_combo_box, 3, 2)
		# Last row: Draw button
		self.btn_draw = QPushButton("Draw")
		self.btn_draw.clicked.connect(self.draw_selected)
		ctrl_grid.addWidget(self.btn_draw, 4, 1, 1, 4)

		# --- Right side: dataset management
		# A list widget where user can select dataset(s) to draw on the plot
		self.dataset_list = QListWidget()
		self.dataset_list.setSelectionMode(self.dataset_list.ExtendedSelection)
		self.dataset_list.setSpacing(0)
		for ds in self._datasets:
			list_item = QListWidgetItem(f"{ds.name} (channel {ds.channel})")
			self.dataset_list.addItem(list_item)
			# We want all datasets to be selected at the start
			# because we will immediately plot them
			list_item.setSelected(True)
		ctrl_grid.addWidget(self.dataset_list, 1, 5, 4, 1)

		# --- Phasor plot and roi management --- #
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
		self._draw_semicircle()

		left.addWidget(self._toolbar)
		left.addWidget(self._canvas, stretch=1)

		# Right: Cirlular ROI management panel
		#right = QVBoxLayout()
		#bottom.addLayout(right, stretch=0)

		# TODO: We need to think about how to arrange this ROI management panel.

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
		self._ax.cla()
		self._ax.set_xlim(xlim)
		self._ax.set_ylim(ylim)
		self._ax.set_xscale(xscale)
		self._ax.set_yscale(yscale)
		self._ax.set_aspect(aspect)

		self._ax.set_title("Phasor Plot")
		self._ax.set_xlabel("G, real")
		self._ax.set_ylabel("S, imag")
		self._draw_semicircle()
		self._canvas.draw_idle()

	def draw_selected(self) -> None:
		self.clear_plot() # Clear plot first

		min_count = self.min_count.value()
		max_count = self.max_count.value()
		kernel_size = self.kernel_size.value()
		repetition = self.repetition.value()

		# Get selected row indices
		indices = [self.dataset_list.row(item) for item in self.dataset_list.selectedItems()]

		for idx in indices:
			self.draw_dataset(
				self._datasets[idx],
				min_count,
				max_count,
				kernel_size,
				repetition,
				self.mode_combo_box.currentText()
			)

		self._canvas.draw_idle()

	def draw_dataset(
		self,
		dataset: "Dataset",
		min_photon_count: int = 0,
		max_photon_count: int = int(1e9),
		median_filter_size: int = 3,
		median_filter_repetition: int = 0,
		mode:Literal["scatter","hist2d","contour"] = "contour",
		color = None
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
		# Median filter
		m = dataset.mean; g = dataset.real; s = dataset.imag
		if median_filter_repetition > 0:
			m,g,s = phasor_filter_median(m, g, s, repeat=median_filter_repetition, size=median_filter_size)
		# Photon sum filter
		labels = photon_range_mask(dataset.signal.sum(dim='H'), min_photon_count, max_photon_count)
		mask = (labels == 1)
		# Finalize
		g = g[mask]; s = s[mask]
		match mode:
			case "scatter":
				self._pp.plot(g, s, fmt='.')
			case "hist2d":
				self._pp.hist2d(g, s)
			case "contour":
				self._pp.contour(g, s)

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

	## ------ Internal ------ ##
	def _draw_semicircle(self) -> None:
		self._pp.semicircle(frequency=self.frequency, lifetime=[0.5,1,2,4,8])