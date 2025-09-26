from typing import Optional, Literal, TYPE_CHECKING

from qtpy.QtCore import Signal
from qtpy.QtWidgets import QWidget, QVBoxLayout

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT

from phasorpy.plot import PhasorPlot
from phasorpy.phasor import phasor_filter_median
from flim_studio.core.processing import photon_range_mask

if TYPE_CHECKING:
	from ..sample_manager import Dataset
	from matplotlib.axes import Axes

class PhasorGraphWidget(QWidget):
	"""
	QWidget container for matplotlib figure and phasor plot related APIs.
	"""
	canvasClicked = Signal(float, float)

	def __init__(
		self,
		frequency: float|None = None,
		dpi: int = 120,
		fig_pixels: int = 480,
		parent: QWidget|None = None
	) -> None:
		super().__init__(parent)
		self.dpi = dpi
		self.fig_pixels = fig_pixels
		self.frequency = frequency

		self._build()

	## ------ UI ------ ##
	def _build(self) -> None:
		root = QVBoxLayout(self)

		fsize = self.fig_pixels/self.dpi
		self._fig = Figure(figsize=(fsize, fsize), dpi=self.dpi)
		self._canvas = FigureCanvasQTAgg(self._fig)
		self._toolbar = NavigationToolbar2QT(self._canvas, self)
		self._ax = self._fig.add_subplot(111)
		# Connect canavs click event for placing ROIs
		self._fig.canvas.mpl_connect("button_press_event", self._on_mpl_click)
		# Make PhasorPlot object and hand it control over the axes
		self._pp = PhasorPlot(ax=self._ax, frequency=self.frequency)
		self.draw_idle()

		root.addWidget(self._toolbar)
		root.addWidget(self._canvas, stretch=1)

	## ------ Public API ------ ##
	def get_ax(self) -> "Axes":
		return self._ax

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

	def draw_idle(self) -> None:
		"""Schedule canvas changes to be rendered."""
		self._canvas.draw_idle()

	## ------ Internal ------ ##
	def _on_mpl_click(self, event) -> None:
		"""
		Matplotlib 'button_press_event' handler.
		Emits (g, s) coordinate when the click occurs inside the axes.
		"""
		# Ignore clicks while toolbar is in an active mode (pan/zoom)
		if getattr(self._toolbar, "mode", ""):
			return
		# Ignore if not in our axes (there should only be one but safeguard)
		if event.inaxes is not self._ax:
			return
		if event.xdata is None or event.ydata is None:
			return
		g, s = float(event.xdata), float(event.ydata)
		self.canvasClicked.emit(g, s)

	def _draw_semicircle(self) -> None:
		# We have to give it frequency here because apparently PhasorPlot does not
		# keep track of the frequency value given in init.
		self._pp.semicircle(frequency=self.frequency, lifetime=[0.5,1,2,4,8])