from typing import TYPE_CHECKING

from qtpy.QtWidgets import (
	QWidget,
	QHBoxLayout,
	QVBoxLayout,
	QLabel,
	QPushButton,
	QFormLayout,
	QSpinBox,
	QDoubleSpinBox,
	QGroupBox
)
from qtpy.QtCore import Qt
import numpy as np
from napari import Viewer

from ..config.defaults import Defaults
from ..core import (
	load_signal,
	phasor_from_signal,
	tau_map_from_gs,
	photon_sum,
	photon_range_mask,
	apply_spatial_median
)

# HACK: Gotta clean up imports at some point
from .phasor.calibration_widget import CalibrationWidget
from .phasor.sample_manager_widget import SampleManagerWidget
from .phasor.phasor_plot_widget import PhasorPlotWidget

class PhasorAnalysis(QWidget):
	def __init__(self, viewer:Viewer) -> None:
		super().__init__()
		self.viewer = viewer
		self.setWindowTitle("Phasor Analysis")
		self.defaults = Defaults()
		self._signal = None
		self._phasor = None
		self._calibration = None
		self._g = None
		self._s = None

		self._build()
		#self._test()

	def _build(self) -> None:
		theme = getattr(self.viewer, "theme", "dark")
		layout = QVBoxLayout(self)

		phasor_plot_widget = PhasorPlotWidget(self.viewer)
		phasor_plot_dock = self.viewer.window.add_dock_widget(phasor_plot_widget, name="Phasor Plot", area="right")
		phasor_plot_dock.setFloating(True)
		phasor_plot_dock.setAllowedAreas(Qt.NoDockWidgetArea)

		cal_widget = CalibrationWidget(self)
		sample_manager_widget = SampleManagerWidget(self.viewer, cal_widget.get_calibration(), self)
		sample_manager_widget.set_plot_widget(phasor_plot_widget)
		layout.addWidget(cal_widget)
		layout.addWidget(sample_manager_widget)


	def _test(self) -> None:
		points = [[1,1], [-1,1], [1,-1], [-1,-1]]
		self.viewer.add_points(points)
