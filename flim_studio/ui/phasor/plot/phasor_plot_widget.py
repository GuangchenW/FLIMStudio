from typing import Optional, List, TYPE_CHECKING

import numpy as np

from qtpy.QtWidgets import (
	QWidget,
	QHBoxLayout,
	QVBoxLayout,
)

from .graph import PhasorGraphWidget
from .control_panel import PhasorControlPanel
from .roi_manager import RoiManagerWidget

if TYPE_CHECKING:
	import napari
	from .sample_manager_widget import Dataset

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
		root.addLayout(bottom, stretch=1)
		# Left: PhasorPlot
		# TODO: DPI and pixels from config files?
		self.phasor_graph_widget = PhasorGraphWidget(self.frequency, 120, 480)
		bottom.addWidget(self.phasor_graph_widget, stretch=1)

		# Right: Cirlular ROI management panel
		self.roi_manager = RoiManagerWidget(self.phasor_graph_widget.get_ax(), self.viewer)
		bottom.addWidget(self.roi_manager, stretch=0)

		# Connect ROI manager to the graph click signal
		self.phasor_graph_widget.canvasClicked.connect(self.roi_manager.move_selected_roi)

	## ------ Internal ------ ##
	def _on_plot_phasor(self) -> None:
		datasets = self.control_panel.get_selected_datasets()
		params = self.control_panel.get_params()
		if len(datasets) <= 0: return # Should not happen but safeguard

		self.phasor_graph_widget.clear_plot()
		for ds in datasets:
			self.phasor_graph_widget.draw_dataset(ds, **params)
		self.phasor_graph_widget.draw_idle()