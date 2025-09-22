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
import napari
from napari.viewer import Viewer

from ..config.defaults import Defaults
from ..core import (
	load_signal,
	phasor_from_signal,
	tau_map_from_gs,
	photon_sum,
	photon_range_mask,
	apply_spatial_median
)

from .menu.calibration_widget import CalibrationWidget

class MainPanel(QWidget):
	def __init__(self, viewer:Viewer) -> None:
		super().__init__()
		self.viewer = viewer
		self.setWindowTitle("FLIM Studio")
		self.defaults = Defaults()
		self._signal = None
		self._phasor = None
		self._calibration = None
		self._g = None
		self._s = None

		self._build()

	def _build(self) -> None:
		layout = QVBoxLayout(self)

		ref_widget = CalibrationWidget(self)
		layout.addWidget(ref_widget)
