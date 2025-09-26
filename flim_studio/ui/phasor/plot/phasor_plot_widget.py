from typing import Dict, Optional, List, Literal, TYPE_CHECKING
from dataclasses import dataclass

import numpy as np
from phasorpy.plot import PhasorPlot
from phasorpy.phasor import phasor_filter_median
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT

if TYPE_CHECKING:
	import napari
	from .sample_manager_widget import Dataset
from flim_studio.core.processing import photon_range_mask
from flim_studio.ui.custom import RemoveButton, ColorButton
from .graph import PhasorGraphWidget
from .control_panel import PhasorControlPanel

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
)

class PhasorPlotWidget(QWidget):
	"""
	A QWidget for hosting a phasorpy PhasorPlot and the associated matplotlib figure.
	"""
	def __init__(
		self, 
		viewer: "napari.Viewer",
		datasets: List["Dataset"],
		frequency: float|None = None,
		parent: QWidget|None = None,
	) -> None:
		super().__init__(parent)
		self.viewer = viewer
		self.frequency: float|None = frequency

		self._datasets = datasets

		self._build()

	## ------ UI ------ ##
	def _build(self) -> None:
		root = QVBoxLayout(self)
		root.setContentsMargins(5,5,5,5)

		# Parameters control panel
		self.control_panel = PhasorControlPanel(self._datasets)
		self.control_panel.plotPhasor.connect(self._on_plot_phasor)
		root.addWidget(self.control_panel)

		# Phasor plot and roi management
		bottom = QHBoxLayout()
		root.addLayout(bottom, stretch=1) # We really care about the stretching factor here so safer to be explicit
		# Left: PhasorPlot
		# TODO: DPI and pixels from config files?
		self.phasor_graph_widget = PhasorGraphWidget(self.frequency, 120, 480)
		bottom.addWidget(self.phasor_graph_widget, stretch=1)

		# Right: Cirlular ROI management panel
		#right = QVBoxLayout()
		#bottom.addLayout(right, stretch=0)

		# TODO: We need to think about how to arrange this ROI management panel.

	## ------ Internal ------ ##
	def _on_plot_phasor(self) -> None:
		datasets = self.control_panel.get_selected_datasets()
		params = self.control_panel.get_params()
		if len(datasets) <= 0: return # Should not happen but safeguard

		self.phasor_graph_widget.clear_plot()
		for ds in datasets:
			self.phasor_graph_widget.draw_dataset(ds, **params)
		self.phasor_graph_widget.draw_idle()