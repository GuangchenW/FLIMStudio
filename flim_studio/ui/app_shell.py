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

from flim_studio.config.defaults import Defaults
from flim_studio.core import LayerManager

# HACK: Gotta clean up imports at some point
from .phasor.calibration_widget import CalibrationWidget
from .phasor.sample_manager_widget import SampleManagerWidget

class PhasorAnalysis(QWidget):
	def __init__(self, viewer:Viewer) -> None:
		super().__init__()
		self.viewer = viewer
		self.setWindowTitle("Phasor Analysis")
		LayerManager(self.viewer) # Initialize layer manager singleton
		self.defaults = Defaults()
		self._signal = None
		self._phasor = None
		self._calibration = None
		self._g = None
		self._s = None

		self._build()
		#self._test()

	def _build(self) -> None:
		layout = QVBoxLayout(self)

		cal_widget = CalibrationWidget(self)
		sample_manager_widget = SampleManagerWidget(self.viewer, cal_widget.get_calibration(), self)
		# HACK: I don't like it is doing this here. Maybe move the entire cal widget reference into sample manager
		cal_widget.calibrationChanged.connect(sample_manager_widget._mark_all_stale)
		layout.addWidget(cal_widget)
		layout.addWidget(sample_manager_widget)

